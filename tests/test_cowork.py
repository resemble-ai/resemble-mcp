import base64
import json
import time

import httpx
import pytest
from starlette.testclient import TestClient

import cowork_server as cs

AUTH = {"Authorization": "Bearer test-user-token", "Accept": "application/json, text/event-stream"}
UUID = "12345678abcdef90"


@pytest.fixture(scope="module")
def client():
    with TestClient(cs.create_app(), base_url="http://localhost") as value:
        yield value


@pytest.fixture
def upstream(monkeypatch):
    requests = []
    responses = {}
    real_client = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer test-user-token"
        key = (request.method, request.url.path)
        if key in responses:
            response = responses[key]
            if isinstance(response, Exception):
                raise response
            return response
        if request.url.path == "/api/v2/account":
            return httpx.Response(200, json={"success": True, "item": {}})
        return httpx.Response(200, json={"success": True, "item": {"uuid": UUID, "status": "processing"}})

    monkeypatch.setattr(cs.httpx, "AsyncClient", lambda **kw: real_client(**kw, transport=httpx.MockTransport(handle)))
    return requests, responses


def call(client, name, arguments):
    response = client.post("/cowork/mcp", headers=AUTH,
                           json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                 "params": {"name": name, "arguments": arguments}})
    assert response.status_code == 200
    return response.json()["result"]


def structured(result):
    assert not result.get("isError"), result
    return result.get("structuredContent") or json.loads(result["content"][0]["text"])


def test_no_token_has_oauth_challenge(client):
    response = client.post("/cowork/mcp", json={})
    assert response.status_code == 401
    assert "oauth-protected-resource/cowork/mcp" in response.headers["www-authenticate"]
    metadata = client.get("/.well-known/oauth-protected-resource/cowork/mcp").json()
    assert metadata["authorization_servers"] == ["https://app.resemble.ai"]


def test_invalid_and_revoked_tokens_rejected_on_next_request(client, upstream):
    requests, responses = upstream
    responses[("GET", "/api/v2/account")] = httpx.Response(401, json={"error": "invalid"})
    assert client.post("/cowork/mcp", headers=AUTH, json={}).status_code == 401
    assert len(requests) == 1


def test_discovery_annotations_and_cowork_attachment_schema(client, upstream):
    result = client.post("/cowork/mcp", headers=AUTH,
                         json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).json()["result"]
    assert len(result["tools"]) == 7
    for tool in result["tools"]:
        a = tool["annotations"]
        assert a["readOnlyHint"] == tool["name"].startswith("get_")
        assert a["idempotentHint"] == a["readOnlyHint"]
        assert a["destructiveHint"] is False
        assert all("description" in prop for prop in tool["inputSchema"]["properties"].values())
    upload = next(t for t in result["tools"] if t["name"] == "submit_media_detection")
    assert upload["inputSchema"]["properties"]["file"]["type"] == "string"
    assert upload["inputSchema"]["properties"]["file"]["contentEncoding"] == "base64"
    signal = next(t for t in result["tools"] if t["name"] == "score_signal_content")
    assert signal["inputSchema"]["properties"]["file"]["type"] == "string"
    assert signal["inputSchema"]["properties"]["file"]["contentEncoding"] == "base64"
    assert signal["inputSchema"]["properties"]["text"]["maxLength"] == 20000


def test_submit_and_poll_are_separate(client, upstream):
    requests, _ = upstream
    result = structured(call(client, "submit_media_detection", {"url": "https://example.org/audio.wav"}))
    assert result["uuid"] == UUID and not result["completed"]
    assert [(r.method, r.url.path) for r in requests] == [("GET", "/api/v2/account"), ("POST", "/api/v2/detect")]


def test_file_is_uploaded_directly_without_public_hosting(client, upstream):
    requests, _ = upstream
    structured(call(client, "submit_media_detection", {
        "file": base64.b64encode(b"test-media-bytes").decode(), "filename": "sample.wav", "zero_retention_mode": True,
    }))
    request = requests[-1]
    assert "multipart/form-data" in request.headers["content-type"]
    assert b"test-media-bytes" in request.content
    assert b'name="zero_retention_mode"\r\n\r\ntrue' in request.content


@pytest.mark.parametrize("arguments", [
    {}, {"url": "https://example.org/a.wav", "file": "AAAA", "filename": "a.wav"},
    {"url": "http://example.org/a.wav"}, {"url": "https://127.0.0.1/a.wav"},
    {"url": "https://user:password@example.org/a.wav"}, {"url": "https://metadata.internal/a.wav"},
    {"file": "!invalid!", "filename": "a.wav"}, {"file": "AAAA", "filename": "../a.wav"},
])
def test_invalid_media_rejected_before_submission(client, upstream, arguments):
    requests, _ = upstream
    result = call(client, "submit_media_detection", arguments)
    assert result["isError"]
    assert all(r.method == "GET" for r in requests)


def test_processing_has_no_partial_verdict(client, upstream):
    _, responses = upstream
    responses[("GET", f"/api/v2/detect/{UUID}")] = httpx.Response(200, json={"item": {
        "status": "processing", "metrics": {"label": "fake", "score": 0.9}, "uuid": UUID,
    }})
    result = structured(call(client, "get_media_detection", {"uuid": UUID}))
    assert "metrics" not in result and not result["completed"]


def test_completed_preserves_zero_and_mixed_modalities(client, upstream):
    _, responses = upstream
    responses[("GET", f"/api/v2/detect/{UUID}")] = httpx.Response(200, json={"item": {
        "status": "completed", "metrics": {"label": "real", "aggregated_score": 0},
        "video_metrics": {"label": "fake", "score": 0.9}, "url": "https://example.org/private?secret=1",
    }})
    result = structured(call(client, "get_media_detection", {"uuid": UUID}))
    assert result["metrics"]["aggregated_score"] == 0
    assert result["metrics"]["assessment_available"] is True
    assert result["metrics"]["label"] == "real"
    assert result["video_metrics"]["label"] == "fake"
    assert "url" not in result


@pytest.mark.parametrize("scores", [[None], [-1], [], None])
def test_completed_unscored_audio_is_unavailable_without_hiding_video(client, upstream, scores):
    _, responses = upstream
    responses[("GET", f"/api/v2/detect/{UUID}")] = httpx.Response(200, json={"item": {
        "uuid": UUID, "status": "completed", "media_type": "video",
        "metrics": {"label": "real", "score": scores, "aggregated_score": -1.0,
                    "consistency": -1.0, "duration": -1.0},
        "video_metrics": {"label": "Real", "score": 0.04680093312396712},
    }})
    result = structured(call(client, "get_media_detection", {"uuid": UUID}))
    assert result["completed"] is True
    assert result["metrics"]["assessment_available"] is False
    assert result["metrics"]["label"] == "unavailable"
    assert result["metrics"]["reported_label"] == "real"
    assert result["metrics"]["score"] == scores
    assert result["video_metrics"] == {"label": "Real", "score": 0.04680093312396712}


def test_zero_audio_chunk_score_remains_available():
    result = cs.summarize({"status": "completed", "metrics": {"label": "real", "score": [None, 0]}})
    assert result["metrics"]["assessment_available"] is True
    assert result["metrics"]["label"] == "real"


def test_text_abstention_and_no_echo(client, upstream):
    requests, responses = upstream
    result = structured(call(client, "submit_text_detection", {"text": "too short"}))
    assert result["status"] == "not_scored"
    assert len(requests) == 1
    responses[("GET", f"/api/v2/text_detect/{UUID}")] = httpx.Response(200, json={"item": {
        "status": "completed", "prediction": "human", "confidence": 0.95, "text_content": "private original",
    }})
    result = structured(call(client, "get_text_detection", {"uuid": UUID}))
    assert result["prediction"] == "human" and result["confidence"] == 0.95
    assert "text_content" not in result


def test_question_waits_for_completed_detection(client, upstream):
    requests, _ = upstream
    assert call(client, "submit_detection_question", {"detect_uuid": UUID, "query": "Explain"})["isError"]
    assert all(r.method == "GET" for r in requests)


def test_completed_question_roundtrip(client, upstream):
    _, responses = upstream
    responses[("GET", f"/api/v2/detect/{UUID}")] = httpx.Response(200, json={"item": {"status": "completed"}})
    result = structured(call(client, "submit_detection_question", {"detect_uuid": UUID, "query": "Explain"}))
    assert result["uuid"] == UUID and result["detect_uuid"] == UUID
    responses[("GET", f"/api/v2/detects/{UUID}/intelligence/{UUID}")] = httpx.Response(200, json={"item": {"status": "completed", "answer": "Model evidence"}})
    result = structured(call(client, "get_detection_answer", {"detect_uuid": UUID, "question_uuid": UUID}))
    assert result["answer"] == "Model evidence"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_upstream_errors_do_not_retry_or_leak_body(client, upstream, status):
    requests, responses = upstream
    responses[("POST", "/api/v2/detect")] = httpx.Response(status, text="secret-token-and-private-data")
    result = call(client, "submit_media_detection", {"url": "https://example.org/a.wav"})
    assert result["isError"]
    assert "secret-token-and-private-data" not in str(result)
    assert sum(r.method == "POST" for r in requests) == 1


def test_timeout_is_unknown_not_retry(client, upstream):
    requests, responses = upstream
    responses[("POST", "/api/v2/detect")] = httpx.ReadTimeout("sensitive-url")
    result = call(client, "submit_media_detection", {"url": "https://example.org/a.wav"})
    assert result["isError"] and "unknown" in result["content"][0]["text"]
    assert sum(r.method == "POST" for r in requests) == 1


def test_oversized_body_rejected(client, upstream, monkeypatch):
    monkeypatch.setattr(cs, "MAX_BODY_BYTES", 20)
    assert client.post("/cowork/mcp", headers=AUTH, content=b"x" * 21).status_code == 413


@pytest.mark.parametrize("uuid", ["../account", "abc?token=secret", "", "a" * 41])
def test_ids_cannot_change_upstream_route(client, upstream, uuid):
    requests, _ = upstream
    assert call(client, "get_media_detection", {"uuid": uuid})["isError"]
    assert len(requests) == 1


@pytest.mark.parametrize("verdict", ["safe", "suspicious", "fraud"])
def test_signal_text_evidence_and_source_coverage_without_fetching(client, upstream, verdict):
    import hashlib
    requests, responses = upstream
    responses[("POST", "/api/v2/signal")] = httpx.Response(200, json={"item": {
        "id": 42, "input_modality": "text", "verdict": verdict,
        "top_category": {"name": "Reference category", "score": 0},
        "benign_score": 0, "text": "private echo", "text_preview": "private preview",
        "examples": ["reference phrase"], "top_matches": [{"text": "reference example", "score": 0.8}],
    }})
    text = "A public source passage, supplied exactly as retrieved."
    source = "https://example.org/article"
    result = structured(call(client, "score_signal_content", {"text": text, "source_url": source}))
    assert result["verdict"] == verdict and result["assessment_available"] is True
    assert result["status"] == "completed" and result["id"] == 42
    assert result["top_category"]["score"] == 0 and result["benign_score"] == 0
    assert "text" not in result and "text_preview" not in result
    assert result["top_matches"][0]["text"] == "reference example"
    assert result["coverage"] == {"input_kind": "text", "characters_submitted": len(text),
        "scope": "submitted_content_only", "source_url": source,
        "content_sha256": hashlib.sha256(text.encode()).hexdigest()}
    assert [(r.method, r.url.path) for r in requests] == [("GET", "/api/v2/account"), ("POST", "/api/v2/signal")]
    assert json.loads(requests[-1].content) == {"text": text}


def test_signal_workspace_file_upload(client, upstream):
    requests, responses = upstream
    responses[("POST", "/api/v2/signal")] = httpx.Response(200, json={"item": {
        "id": 43, "input_modality": "image", "verdict": "fraud",
        "top_category": {"name": "Impersonation", "score": 0.9},
    }})
    result = structured(call(client, "score_signal_content", {
        "file": base64.b64encode(b"fixture-bytes").decode(), "filename": "fixture.png"}))
    assert result["coverage"]["bytes_submitted"] == 13
    assert result["coverage"]["filename"] == "fixture.png"
    assert result["input_modality"] == "image"
    assert b'filename="fixture.png"' in requests[-1].content
    assert b"fixture-bytes" in requests[-1].content
    assert b"image/png" in requests[-1].content


@pytest.mark.parametrize("arguments", [
    {}, {"text": "  "}, {"text": "https://example.org"},
    {"text": "text", "file": "AAAA", "filename": "file.png"},
    {"text": "  ", "file": "AAAA", "filename": "file.png"},
    {"text": "text", "filename": "file.png"}, {"text": "a" * 20001},
    {"text": "text", "source_url": "https://user:secret@example.org/"},
    {"text": "text", "source_url": "https://127.0.0.1/"},
    {"file": "AAAA", "filename": "../file.png"}, {"file": "!", "filename": "file.png"},
])
def test_signal_invalid_inputs_never_reach_signal(client, upstream, arguments):
    requests, _ = upstream
    assert call(client, "score_signal_content", arguments)["isError"]
    assert all(r.method == "GET" for r in requests)


@pytest.mark.parametrize("item", [
    {}, {"id": 12, "verdict": "safe"},
    {"verdict": "safe", "top_category": {"name": "Test", "score": None}},
    {"verdict": "unknown", "top_category": {"name": "Test", "score": 0.9}},
    {"status": "processing", "verdict": "safe", "top_category": {"name": "Test", "score": 0.9}},
])
def test_signal_incomplete_result_is_never_safe(client, upstream, item):
    _, responses = upstream
    responses[("POST", "/api/v2/signal")] = httpx.Response(200, json={"item": item})
    result = structured(call(client, "score_signal_content", {"text": "Test content"}))
    assert result["assessment_available"] is False and result["status"] == "unavailable"
    assert "verdict" not in result


@pytest.mark.parametrize("failure", [403, 429, 500, "timeout"])
def test_signal_failures_are_not_retried_or_safe(client, upstream, failure):
    requests, responses = upstream
    responses[("POST", "/api/v2/signal")] = (httpx.ReadTimeout("sensitive upstream details")
        if failure == "timeout" else httpx.Response(failure, text="sensitive upstream details"))
    result = call(client, "score_signal_content", {"text": "Test content"})
    assert result["isError"] and "sensitive upstream details" not in str(result)
    assert sum(r.method == "POST" for r in requests) == 1
