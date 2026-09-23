"""
Resemble AI Action MCP Server — Detect + Intelligence execution tools.

Runs alongside the docs server (server.py). Where the docs server answers questions
ABOUT Resemble, this one RUNS Resemble: deepfake detection, media intelligence,
audio source tracing, AI-text detection, watermarking, and Agent Detection
(person-vs-AI-agent website visitor analytics) against
https://app.resemble.ai/api/v2.

Transport: Streamable HTTP (stateless), mounted at /mcp by server.py's SSE runner.

Security model — BYO key, zero storage:
- Every request must carry the caller's own Resemble API key
  (`Authorization: Bearer <key>` or `X-Resemble-API-Key` header).
- The key is used in-memory for the single upstream call and never stored,
  logged, or echoed. The server keeps no database and no service key.
- `callback_url` is intentionally NOT exposed (webhooks don't map onto MCP and
  accepting arbitrary callback targets from agents is an exfiltration vector).
  Async jobs are polled to completion server-side instead.
"""

import ipaddress
import json
import re
from typing import Any, Optional
from urllib.parse import urlencode, urlparse

import anyio
import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

RESEMBLE_API_BASE = "https://app.resemble.ai/api/v2"
TERMINAL_STATUSES = {"completed", "failed", "error", "cancelled", "success"}
MAX_WAIT_CEILING = 180  # hard cap on server-side polling, seconds
UPSTREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)

# Text detection. The detector abstains below 25 words (no threshold separates
# casual human writing from AI text down there), and the public API rejects
# such requests with a 400 - so short-circuit locally and never spend a call.
TEXT_MIN_WORDS = 25
TEXT_MAX_CHARS = 100_000
# The text model scales to zero; the first job after idle sits in `processing`
# for minutes while it loads (3-4 by spec, ~9 observed in production on
# 2026-09-02). Media polling's ceiling is too short for that.
TEXT_WAIT_CEILING = 300

# DNS-rebinding protection: the SDK's TrustedHost check defaults to
# localhost-only, which 421s every request once deployed behind the real
# domain. Allow the public host (+ local dev) explicitly.
_TRANSPORT_SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp.resemble.ai",
        "mcp.resemble.ai:443",
        "localhost:*",
        "127.0.0.1:*",
    ],
    allowed_origins=[
        "https://mcp.resemble.ai",
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
)

action_mcp = FastMCP(
    "resemble-actions",
    transport_security=_TRANSPORT_SECURITY,
    instructions=(
        "Execute Resemble AI media-safety operations: deepfake detection on audio/"
        "image/video, AI-generated text detection (essays, emails, posts, reviews), "
        "media intelligence (transcription, speaker info, emotion, misinformation), "
        "audio source tracing, and invisible watermarking. Media "
        "must be a public HTTPS URL; text is sent inline and needs 25+ words. "
        "Detect Agents run managed multi-step "
        "investigations (insurance claim, breaking news, ID, document, evidence, "
        "social content) that wrap detection in evidence gathering and a written "
        "assessment. Agent Detection (tools prefixed agent_detection_) is a "
        "different product: it tells a website whether each visitor is a person "
        "or an AI agent; use it to set up a site's snippet and read its visitor "
        "analytics. Authenticate every request with your Resemble API key as a "
        "Bearer token. Never declare media real or fake, or text AI- or human-"
        "written, without a completed detection result; always report the label "
        "with its score (for text: prediction with its confidence)."
    ),
    stateless_http=True,
    json_response=True,
)


# --------------------------------------------------------------------------- #
# Auth + validation helpers
# --------------------------------------------------------------------------- #
def _api_key_from_request(ctx: Context) -> str:
    request = ctx.request_context.request
    if request is None:
        raise ValueError("No HTTP request in context.")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key:
            return key
    key = (request.headers.get("x-resemble-api-key") or "").strip()
    if key:
        return key
    raise ValueError(
        "Missing Resemble API key. Send it as 'Authorization: Bearer <RESEMBLE_API_KEY>' "
        "(or 'X-Resemble-API-Key'). Get a key at https://app.resemble.ai (Account -> API)."
    )


_PRIVATE_HOST_RE = re.compile(r"^(localhost|.*\.local|.*\.internal)$", re.I)


def _validate_media_url(url: str) -> str:
    clean = (url or "").strip()
    parsed = urlparse(clean)
    if parsed.scheme != "https":
        raise ValueError("Media URL must be a public https:// link.")
    host = parsed.hostname or ""
    if _PRIVATE_HOST_RE.match(host):
        raise ValueError("Media URL must be publicly reachable (not a local/internal host).")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Media URL must not point at a private or reserved IP.")
    except ValueError as exc:
        if "Media URL" in str(exc):
            raise
        # host is a domain name, not an IP — fine
    return clean


def _clamp(value: Optional[float], lo: float, hi: float, default: float) -> float:
    if value is None:
        return default
    return max(lo, min(hi, float(value)))


def _sanitize(data: Any, max_inline: int = 200) -> Any:
    """Replace huge inline base64 data-URIs (heatmaps) with short placeholders."""
    if isinstance(data, dict):
        return {k: _sanitize(v, max_inline) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize(v, max_inline) for v in data]
    if isinstance(data, str) and data.startswith("data:") and len(data) > max_inline:
        return f"<inline base64 omitted - {len(data)} chars>"
    return data


def _item(data: Any) -> dict:
    if isinstance(data, dict) and isinstance(data.get("item"), dict):
        return data["item"]
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------- #
# Upstream client (key used in-memory only; never logged)
# --------------------------------------------------------------------------- #
async def _request(api_key: str, method: str, path: str,
                   body: Optional[dict] = None,
                   extra_headers: Optional[dict] = None) -> Any:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        resp = await client.request(
            method, f"{RESEMBLE_API_BASE}/{path.lstrip('/')}", json=body, headers=headers
        )
    if resp.status_code in (401, 403):
        raise ValueError("Resemble authentication failed - check your API key.")
    if resp.status_code == 429:
        raise ValueError("Rate limited by the Resemble API (HTTP 429) - back off and retry.")
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:500]}
    if resp.status_code >= 400:
        detail = data.get("message") if isinstance(data, dict) else None
        raise ValueError(f"Resemble API error (HTTP {resp.status_code}): {detail or path}")
    return data


_PRESET_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def _agent_error(status_code: int, body: str) -> ValueError:
    """Pre-stream failures on an agent run come back as plain JSON, not SSE."""
    try:
        detail = (json.loads(body) or {}).get("message")
    except ValueError:
        detail = None
    if status_code in (401, 403):
        return ValueError(f"Resemble authentication or access failed - {detail or 'check your API key.'}")
    if status_code == 402:
        return ValueError(
            f"Detect Agent run not permitted (HTTP 402): {detail or 'billing or credits blocked the run'}. "
            "Runs need the D-Agent tier bundle or a remaining free run - check "
            "free_runs_remaining / entitled from list_detect_agents."
        )
    if status_code == 404:
        return ValueError(f"Unknown Detect Agent - {detail or 'check preset_id against list_detect_agents.'}")
    return ValueError(f"Resemble API error (HTTP {status_code}): {detail or 'agent run failed'}")


async def _stream_agent_run(api_key: str, preset_id: str, fields: list[tuple[str, str]],
                            max_wait_seconds: float) -> dict:
    """POST a multipart agent run and fold its SSE stream into a compact summary.

    Token/narration frames are dropped: they are large and the run is persisted
    server-side, so the full transcript stays retrievable via
    get_detect_agent_run even when this call gives up early.
    """
    budget = _clamp(max_wait_seconds, 5, MAX_WAIT_CEILING, 180)
    # (None, value) makes httpx emit a plain multipart field with no filename.
    files = [(name, (None, value)) for name, value in fields]
    summary: dict[str, Any] = {
        "run_id": None, "label": None, "score": None, "report_url": None,
        "agent_ran": None, "verdict": None, "tools_used": [], "completed": False,
        "timed_out": False, "error": None,
    }

    def absorb_detect(detect: Any) -> None:
        """Detect evidence arrives either as a standalone `detect` frame or nested
        in the run_detect `tool_result`; observed runs only carry the latter."""
        if not isinstance(detect, dict):
            return
        summary["label"] = detect.get("label", summary["label"])
        summary["score"] = detect.get("score", summary["score"])
        summary["report_url"] = detect.get("report_url", summary["report_url"])

    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        async with client.stream(
            "POST", f"{RESEMBLE_API_BASE}/agents/{preset_id}/run",
            files=files,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"},
        ) as resp:
            if resp.status_code >= 400:
                raise _agent_error(resp.status_code, (await resp.aread()).decode("utf-8", "replace"))
            with anyio.move_on_after(budget):
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        frame = json.loads(line[5:].strip())
                    except ValueError:
                        continue
                    if not isinstance(frame, dict):
                        continue
                    kind = frame.get("type")
                    if kind == "run_started":
                        summary["run_id"] = frame.get("run_id")
                    elif kind == "detect":
                        absorb_detect(frame.get("detect"))
                    elif kind == "gate":
                        summary["agent_ran"] = frame.get("agent_ran")
                    elif kind == "tool_call":
                        tool = frame.get("tool")
                        if tool and tool not in summary["tools_used"] and len(summary["tools_used"]) < 25:
                            summary["tools_used"].append(tool)
                    elif kind == "tool_result":
                        absorb_detect(frame.get("detect"))
                    elif kind == "final_verdict":
                        summary["verdict"] = frame.get("intelligence")
                    elif kind == "error":
                        summary["error"] = frame.get("message")
                    elif kind == "done":
                        # A failed investigation still ends on `done` after its
                        # error frame; don't report that as a clean completion.
                        summary["completed"] = summary["error"] is None
                        break
    summary["timed_out"] = not summary["completed"] and summary["error"] is None
    return _sanitize(summary)


async def _poll(api_key: str, path: str, max_wait_seconds: float,
                ceiling: float = MAX_WAIT_CEILING,
                ctx: Optional[Context] = None) -> Any:
    budget = _clamp(max_wait_seconds, 1, ceiling, 120)
    elapsed, delay = 0.0, 2.0
    last = await _request(api_key, "GET", path)
    while True:
        status = str(_item(last).get("status") or "").lower()
        if not status or status in TERMINAL_STATUSES or elapsed >= budget:
            return last
        if ctx is not None:
            # Long waits (text cold start) outlive many clients' request
            # timeouts; progress frames let clients that honour them keep
            # the call alive. No-op when the client sent no progress token.
            try:
                await ctx.report_progress(elapsed, budget)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass
        await anyio.sleep(delay)
        elapsed += delay
        delay = min(10.0, delay + 1.0)
        last = await _request(api_key, "GET", path)


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@action_mcp.tool()
async def detect_deepfake(
    url: str,
    ctx: Context,
    run_intelligence: bool = False,
    audio_source_tracing: bool = False,
    visualize: bool = False,
    use_reverse_search: bool = False,
    use_ood_detector: bool = False,
    zero_retention_mode: bool = False,
    model_type: str = "auto",
    max_wait_seconds: int = 120,
) -> dict:
    """Detect whether media (audio, image, or video) at a public HTTPS URL is a
    deepfake / AI-generated. Polls to completion and returns the verdict label,
    confidence score, and full result. Optional flags add media intelligence,
    audio source tracing, visualization, reverse image search (images),
    out-of-distribution detection, and zero-retention (auto-delete media after
    analysis). model_type: auto | image | talking_head."""
    api_key = _api_key_from_request(ctx)
    body: dict[str, Any] = {"url": _validate_media_url(url)}
    for flag, key in (
        (run_intelligence, "intelligence"),
        (audio_source_tracing, "audio_source_tracing"),
        (visualize, "visualize"),
        (use_reverse_search, "use_reverse_search"),
        (use_ood_detector, "use_ood_detector"),
        (zero_retention_mode, "zero_retention_mode"),
    ):
        if flag:
            body[key] = True
    if model_type and model_type != "auto":
        if model_type not in ("image", "talking_head"):
            raise ValueError("model_type must be auto, image, or talking_head.")
        body["model_types"] = model_type

    submitted = await _request(api_key, "POST", "/detect", body)
    uuid = _item(submitted).get("uuid")
    result = await _poll(api_key, f"/detect/{uuid}", max_wait_seconds) if uuid else submitted
    item = _item(result)
    metrics = item.get("metrics") or item.get("image_metrics") or item.get("video_metrics") or {}
    return {
        "status": item.get("status"),
        "label": metrics.get("label"),
        "score": metrics.get("aggregated_score") or metrics.get("score"),
        "uuid": uuid,
        "result": _sanitize(result),
    }


@action_mcp.tool()
async def get_detection(uuid: str, ctx: Context, max_wait_seconds: int = 60) -> dict:
    """Fetch a detection by UUID, polling until it completes (bounded). Use after
    detect_deepfake when a long job exceeded its wait budget."""
    api_key = _api_key_from_request(ctx)
    if not re.fullmatch(r"[0-9a-fA-F-]{8,40}", (uuid or "").strip()):
        raise ValueError("uuid must be a Resemble detection id.")
    result = await _poll(api_key, f"/detect/{uuid.strip()}", max_wait_seconds)
    return {"result": _sanitize(result)}


def _text_summary(uuid: Optional[str], result: Any, word_count: Optional[int] = None) -> dict:
    item = _item(result)
    status = item.get("status")
    # The API echoes the submitted text back; the caller already has it and it
    # can be 100k chars, so keep it out of the tool result.
    trimmed = _sanitize(result)
    if isinstance(trimmed, dict) and isinstance(trimmed.get("item"), dict):
        trimmed["item"] = {k: v for k, v in trimmed["item"].items() if k != "text_content"}
    out: dict[str, Any] = {
        "status": status,
        "prediction": item.get("prediction"),
        "confidence": item.get("confidence"),
        "uuid": uuid,
        "result": trimmed,
    }
    if word_count is not None:
        out["word_count"] = word_count
    if str(status or "").lower() == "processing":
        out["message"] = (
            "Still processing. The text model cold-starts when idle and jobs queue "
            "behind it, so a result can take several minutes (up to ~10 observed); "
            "call get_text_detection with this uuid to keep waiting."
        )
    elif item.get("prediction") == "uncertain":
        out["message"] = "The detector abstained: not enough text to judge. Do not report this as human or AI."
    return out


@action_mcp.tool()
async def detect_ai_text(
    text: str,
    ctx: Context,
    threshold: float = 0.5,
    zero_retention_mode: bool = False,
    max_wait_seconds: int = 240,
) -> dict:
    """Detect whether TEXT (an essay, email, post, review, comment, article) was
    written by an AI language model. Needs at least 25 words: shorter text comes
    back as prediction 'uncertain' with no model call - concatenate several
    messages from the same author to reach the minimum. Returns prediction
    ('ai' | 'human'), confidence (how sure the model is of that prediction; it
    is NOT an AI probability, so 'human' at 0.95 means strongly human), and the
    full result. Only the first ~400 words are read; chunk longer documents.
    A result can take several minutes when the model is cold or jobs are
    queued - if status is still 'processing' when the wait budget ends, resume
    with get_text_detection(uuid). Detection is probabilistic, not proof of authorship."""
    api_key = _api_key_from_request(ctx)
    clean = (text or "").strip()
    if not clean:
        raise ValueError("text is required.")
    if len(clean) > TEXT_MAX_CHARS:
        raise ValueError(
            f"text must be {TEXT_MAX_CHARS:,} characters or fewer (got {len(clean):,}). "
            "Split it into ~300-word chunks and submit each."
        )
    word_count = len(clean.split())
    if word_count < TEXT_MIN_WORDS:
        return {
            "status": "not_scored",
            "prediction": "uncertain",
            "confidence": 0.0,
            "reason": "insufficient_text",
            "word_count": word_count,
            "min_words": TEXT_MIN_WORDS,
            "message": (
                f"Not enough text to judge: {word_count} words, the detector needs at least "
                f"{TEXT_MIN_WORDS}. Combine several messages from the same author and retry. "
                "Do not report this as human or AI."
            ),
        }
    body: dict[str, Any] = {"text": clean, "threshold": _clamp(threshold, 0.0, 1.0, 0.5)}
    if zero_retention_mode:
        body["zero_retention_mode"] = True
    submitted = await _request(api_key, "POST", "/text_detect", body)
    uuid = _item(submitted).get("uuid")
    result = (
        await _poll(api_key, f"/text_detect/{uuid}", max_wait_seconds,
                    ceiling=TEXT_WAIT_CEILING, ctx=ctx)
        if uuid else submitted
    )
    return _text_summary(uuid, result, word_count)


@action_mcp.tool()
async def get_text_detection(uuid: str, ctx: Context, max_wait_seconds: int = 240) -> dict:
    """Fetch a text detection by UUID, polling until it completes (bounded). Use
    after detect_ai_text returned status 'processing' - typically a cold start."""
    api_key = _api_key_from_request(ctx)
    clean_uuid = (uuid or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{8,40}", clean_uuid):
        raise ValueError("uuid must be a Resemble text detection id.")
    result = await _poll(api_key, f"/text_detect/{clean_uuid}", max_wait_seconds,
                         ceiling=TEXT_WAIT_CEILING, ctx=ctx)
    return _text_summary(clean_uuid, result)


@action_mcp.tool()
async def analyze_media(
    url: str,
    ctx: Context,
    media_type: str = "auto",
    structured_json: bool = True,
    max_wait_seconds: int = 120,
) -> dict:
    """Analyze media for structured intelligence: transcription, translation,
    language, speaker info, emotion, scene description, abnormalities, and
    misinformation analysis. media_type: auto | audio | video | image."""
    api_key = _api_key_from_request(ctx)
    body: dict[str, Any] = {"url": _validate_media_url(url), "json": bool(structured_json)}
    if media_type and media_type != "auto":
        if media_type not in ("audio", "video", "image"):
            raise ValueError("media_type must be auto, audio, video, or image.")
        body["media_type"] = media_type
    result = await _request(api_key, "POST", "/intelligence", body)
    item = _item(result)
    status = str(item.get("status") or "").lower()
    if item.get("uuid") and status and status not in TERMINAL_STATUSES:
        try:
            result = await _poll(api_key, f"/intelligence/{item['uuid']}", max_wait_seconds)
        except ValueError:
            pass  # poll path can vary; return the submit payload
    return {"result": _sanitize(result)}


@action_mcp.tool()
async def ask_about_detection(
    detect_uuid: str, query: str, ctx: Context, max_wait_seconds: int = 120
) -> dict:
    """Ask a natural-language question about a COMPLETED detection (e.g. 'how
    confident is the model that this is fake?'). Returns the grounded answer."""
    api_key = _api_key_from_request(ctx)
    clean_uuid = (detect_uuid or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{8,40}", clean_uuid):
        raise ValueError("detect_uuid must be a Resemble detection id.")
    if not (query or "").strip():
        raise ValueError("query is required.")
    submitted = await _request(
        api_key, "POST", f"/detects/{clean_uuid}/intelligence", {"query": query.strip()}
    )
    q_uuid = _item(submitted).get("uuid")
    result = (
        await _poll(api_key, f"/detects/{clean_uuid}/intelligence/{q_uuid}", max_wait_seconds)
        if q_uuid else submitted
    )
    item = _item(result)
    return {"answer": item.get("answer"), "status": item.get("status"),
            "result": _sanitize(result)}


@action_mcp.tool()
async def detect_watermark(url: str, ctx: Context) -> dict:
    """Check whether media at a public HTTPS URL carries a Resemble invisible
    watermark (audio-first; per-channel verdict for audio)."""
    api_key = _api_key_from_request(ctx)
    try:
        result = await _request(
            api_key, "POST", "/watermark/detect",
            {"url": _validate_media_url(url)}, {"Prefer": "wait"},
        )
    except ValueError as exc:
        if "internal error" in str(exc).lower():
            raise ValueError(
                f"{exc} - watermark checks work reliably for audio; some image/video "
                "inputs are unsupported."
            ) from exc
        raise
    item = _item(result)
    has = (item.get("metrics") or {}).get("has_watermark", item.get("has_watermark"))
    found = any(has.values()) if isinstance(has, dict) else bool(has)
    return {"has_watermark": found, "result": _sanitize(result)}


@action_mcp.tool()
async def apply_watermark(
    url: str,
    ctx: Context,
    strength: float = 0.2,
    custom_message: str = "",
    max_wait_seconds: int = 120,
) -> dict:
    """Embed an invisible Resemble provenance watermark into media (audio-first)
    and return the watermarked media URL. strength 0.0-1.0 (image/video only)."""
    api_key = _api_key_from_request(ctx)
    body: dict[str, Any] = {"url": _validate_media_url(url),
                            "strength": _clamp(strength, 0.0, 1.0, 0.2)}
    if (custom_message or "").strip():
        body["custom_message"] = custom_message.strip()[:128]
    result = await _request(api_key, "POST", "/watermark/apply", body, {"Prefer": "wait"})
    item = _item(result)
    if not (item.get("watermarked_media") or item.get("url")) and item.get("uuid"):
        try:
            result = await _poll(
                api_key, f"/watermark/apply/{item['uuid']}/result", max_wait_seconds
            )
            item = _item(result)
        except ValueError:
            pass
    return {"watermarked_media": item.get("watermarked_media"),
            "result": _sanitize(result)}


@action_mcp.tool()
async def trace_audio_source(uuid: str, ctx: Context) -> dict:
    """Get the audio source-tracing report for a detection (which AI platform
    generated the fake audio). Only available when detection ran with
    audio_source_tracing and labeled the audio fake."""
    api_key = _api_key_from_request(ctx)
    if not re.fullmatch(r"[0-9a-fA-F-]{8,40}", (uuid or "").strip()):
        raise ValueError("uuid must be a Resemble source-tracing/detection id.")
    result = await _request(api_key, "GET", f"/audio_source_tracings/{uuid.strip()}")
    return {"result": _sanitize(result)}


@action_mcp.tool()
async def list_detect_agents(ctx: Context) -> dict:
    """List the managed Detect Agents — investigators that wrap detection in a
    multi-step workflow ending in a written assessment. Returns each agent's
    preset_id plus this team's run allowance (free_runs_remaining, entitled),
    which is worth checking before starting a run."""
    api_key = _api_key_from_request(ctx)
    result = await _request(api_key, "GET", "/agents")
    items = result.get("items") if isinstance(result, dict) else None
    return {
        "agents": [
            {"preset_id": a.get("preset_id"), "name": a.get("name"),
             "tier": a.get("tier"), "tagline": a.get("tagline")}
            for a in (items or []) if isinstance(a, dict)
        ],
        "free_runs_remaining": (result or {}).get("free_runs_remaining"),
        "free_runs_limit": (result or {}).get("free_runs_limit"),
        "entitled": (result or {}).get("entitled"),
    }


@action_mcp.tool()
async def run_detect_agent_investigation(
    preset_id: str,
    url: str,
    ctx: Context,
    query: str = "",
    check_urls: str = "",
    max_wait_seconds: int = 180,
) -> dict:
    """Run a managed Detect Agent investigation against media at a public HTTPS
    URL and return its verdict. preset_id is one of: investigate_social_content,
    review_insurance_claim, verify_breaking_news, verify_document,
    verify_evidence, verify_id (confirm with list_detect_agents). query states
    the investigation objective; check_urls adds URLs for the agent to check.

    Consumes a run of the team's allowance. `label`/`score` are the Detect
    evidence and are the only basis for an authenticity claim; `verdict` is the
    agent's written assessment. If timed_out is true the investigation is still
    running server-side — retrieve it later with get_detect_agent_run."""
    api_key = _api_key_from_request(ctx)
    clean_preset = (preset_id or "").strip()
    if not _PRESET_ID_RE.match(clean_preset):
        raise ValueError("preset_id must be a Detect Agent identifier, e.g. verify_document.")
    fields = [("url", _validate_media_url(url))]
    if (query or "").strip():
        fields.append(("query", query.strip()))
    if (check_urls or "").strip():
        fields.append(("check_urls", check_urls.strip()))
    return await _stream_agent_run(api_key, clean_preset, fields, max_wait_seconds)


@action_mcp.tool()
async def get_detect_agent_run(preset_id: str, run_id: str, ctx: Context) -> dict:
    """Fetch a persisted Detect Agent investigation by run_id, including its full
    event transcript. Use after run_detect_agent_investigation reported
    timed_out, or to re-read an earlier investigation."""
    api_key = _api_key_from_request(ctx)
    clean_preset = (preset_id or "").strip()
    clean_run = (run_id or "").strip()
    if not _PRESET_ID_RE.match(clean_preset):
        raise ValueError("preset_id must be a Detect Agent identifier, e.g. verify_document.")
    if not re.fullmatch(r"[0-9a-fA-F-]{8,40}", clean_run):
        raise ValueError("run_id must be the run id returned by run_detect_agent_investigation.")
    result = await _request(api_key, "GET", f"/agents/{clean_preset}/runs/{clean_run}")
    return {"result": _sanitize(result)}


# --------------------------------------------------------------------------- #
# Agent Detection (Porter): is a website visitor a person or an AI agent?
#
# Not to be confused with Detect Agents above. These tools manage the site
# integrations (the publishable key + snippet a website embeds) and read the
# visitor analytics, all with the caller's own API key. The browser-side
# telemetry endpoint takes a publishable key and is deliberately not exposed.
# Key rotation is also left out: it breaks every live page using the old key.
# --------------------------------------------------------------------------- #
_SETTLED_VALUES = {"human", "agent"}
# Raw event streams run to thousands of pointer/key events per visit.
_MAX_INLINE_EVENTS = 200


def _porter_filters(site_id: Optional[int], settled: str, page_path: str,
                    since: str, until: str, search: str) -> dict:
    params: dict = {}
    if site_id:
        params["site_id"] = int(site_id)
    clean_settled = (settled or "").strip().lower()
    if clean_settled:
        if clean_settled not in _SETTLED_VALUES:
            raise ValueError("settled must be 'human' or 'agent'.")
        params["settled"] = clean_settled
    for key, value in (("page_path", page_path), ("from", since), ("to", until), ("q", search)):
        if (value or "").strip():
            params[key] = value.strip()
    return params


def _porter_path(path: str, params: dict) -> str:
    return f"{path}?{urlencode(params)}" if params else path


def _site_summary(site: Any) -> dict:
    if not isinstance(site, dict):
        return {}
    keep = ("id", "name", "domains", "active", "publishable_key", "snippet", "created_at")
    return {k: site.get(k) for k in keep if k in site}


@action_mcp.tool()
async def agent_detection_list_sites(ctx: Context) -> dict:
    """List this team's Agent Detection integrations. Agent Detection tells a
    website whether each visitor is a person or an AI agent (for example a
    personal assistant browsing on someone's behalf). Each integration is one
    website, with the domains its publishable key works on and the one-line
    script snippet to paste into the site's <head>."""
    api_key = _api_key_from_request(ctx)
    result = await _request(api_key, "GET", "/porter/sites")
    items = result.get("items") if isinstance(result, dict) else None
    return {"sites": [s for s in (items or []) if isinstance(s, dict)]}


@action_mcp.tool()
async def agent_detection_create_site(domain: str, ctx: Context, name: str = "") -> dict:
    """Create an Agent Detection integration for a website and return its
    publishable key (pk_live_...) and the script snippet to install. domain is
    the site's domain, e.g. example.com. If the team already has an integration
    for that domain, the existing one is returned instead of a duplicate.

    The publishable key is safe to put in a public web page: it only sends
    telemetry, only from the listed domains. Never put the Resemble API key in
    a page. Paste the snippet into the <head> of every page to cover; the page
    can then listen for the 'porter:verdict' event or call Porter.onVerdict()."""
    api_key = _api_key_from_request(ctx)
    clean = (domain or "").strip()
    if not clean or len(clean) > 253:
        raise ValueError("domain must be a website domain such as example.com.")
    body: dict = {"domain": clean}
    if (name or "").strip():
        body["name"] = name.strip()[:200]
    result = await _request(api_key, "POST", "/porter/sites", body=body)
    return {"site": _site_summary(_item(result))}


@action_mcp.tool()
async def agent_detection_update_site(site_id: int, domains: list[str], ctx: Context,
                                      name: str = "") -> dict:
    """Replace the list of domains an Agent Detection integration's publishable
    key is valid on (for example to add a staging or www host), and optionally
    rename it. domains replaces the whole list, so include every domain to keep;
    at least one is required."""
    api_key = _api_key_from_request(ctx)
    clean = [d.strip() for d in (domains or []) if isinstance(d, str) and d.strip()]
    if not clean:
        raise ValueError("domains must list at least one domain to keep.")
    body: dict = {"domains": clean[:50]}
    if (name or "").strip():
        body["name"] = name.strip()[:200]
    result = await _request(api_key, "PATCH", f"/porter/sites/{int(site_id)}", body=body)
    return {"site": _site_summary(_item(result))}


@action_mcp.tool()
async def agent_detection_get_analytics(
    ctx: Context,
    site_id: Optional[int] = None,
    settled: str = "",
    page_path: str = "",
    since: str = "",
    until: str = "",
) -> dict:
    """Summarise who is visiting a website: people vs AI agents. Returns totals
    (visits, decided, agents, people, agent_share, gated), counts per visitor
    class (human, computer_use_agent, browser_automation, scripted_client), and
    breakdowns by page, day, and network. Use this to show how much traffic
    comes from agents and which pages they use, so the site can be made easier
    for helpful agents and protected from harmful ones.

    Filters are optional: site_id (one integration), settled ('human' or
    'agent'), page_path, and since/until as ISO 8601 times. agent_share is
    agents / decided visits, or null when nothing is decided yet."""
    api_key = _api_key_from_request(ctx)
    params = _porter_filters(site_id, settled, page_path, since, until, "")
    result = await _request(api_key, "GET", _porter_path("/porter/analytics", params))
    if isinstance(result, dict):
        result.pop("success", None)
    return {"analytics": result}


@action_mcp.tool()
async def agent_detection_list_sessions(
    ctx: Context,
    site_id: Optional[int] = None,
    settled: str = "",
    page_path: str = "",
    since: str = "",
    until: str = "",
    search: str = "",
    page: int = 1,
    per_page: int = 25,
) -> dict:
    """List individual website visits, newest first, each with its verdict
    (settled: human, agent, or null while still open), visitor_class,
    p_person, the page, referrer, user agent, and duration. Same filters as
    agent_detection_get_analytics plus a free-text search. per_page max 100."""
    api_key = _api_key_from_request(ctx)
    params = _porter_filters(site_id, settled, page_path, since, until, search)
    params["page"] = max(1, int(page or 1))
    params["per_page"] = int(_clamp(per_page, 1, 100, 25))
    result = await _request(api_key, "GET", _porter_path("/porter/sessions", params))
    if not isinstance(result, dict):
        return {"sessions": []}
    return {
        "sessions": result.get("items") or [],
        "total": result.get("total"),
        "page": result.get("page"),
        "pages": result.get("pages"),
    }


@action_mcp.tool()
async def agent_detection_get_session(session_id: int, ctx: Context,
                                      include_events: bool = False) -> dict:
    """Get one website visit and the evidence behind its verdict: the feature
    vector it was decided from, plain-language observations, and each model
    read. When the visit was recorded, the raw event stream is available;
    it is omitted unless include_events is true, and then capped at the first
    200 events. The verdict is advisory: it comes from browser signals, which
    a determined attacker can fake."""
    api_key = _api_key_from_request(ctx)
    result = await _request(api_key, "GET", f"/porter/sessions/{int(session_id)}")
    item = _item(result)
    recording = item.get("recording")
    if isinstance(recording, dict):
        events = recording.get("events") or []
        if include_events:
            recording["events"] = events[:_MAX_INLINE_EVENTS]
            recording["events_truncated"] = len(events) > _MAX_INLINE_EVENTS
        else:
            recording.pop("events", None)
    return {"session": _sanitize(item)}
