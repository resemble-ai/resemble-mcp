"""
Resemble AI Action MCP Server — Detect + Intelligence execution tools.

Runs alongside the docs server (server.py). Where the docs server answers questions
ABOUT Resemble, this one RUNS Resemble: deepfake detection, media intelligence,
audio source tracing, and watermarking against https://app.resemble.ai/api/v2.

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
import re
from typing import Any, Optional
from urllib.parse import urlparse

import anyio
import httpx
from mcp.server.fastmcp import Context, FastMCP

RESEMBLE_API_BASE = "https://app.resemble.ai/api/v2"
TERMINAL_STATUSES = {"completed", "failed", "error", "cancelled", "success"}
MAX_WAIT_CEILING = 180  # hard cap on server-side polling, seconds
UPSTREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)

action_mcp = FastMCP(
    "resemble-actions",
    instructions=(
        "Execute Resemble AI media-safety operations: deepfake detection on audio/"
        "image/video, media intelligence (transcription, speaker info, emotion, "
        "misinformation), audio source tracing, and invisible watermarking. Media "
        "must be a public HTTPS URL. Authenticate every request with your Resemble "
        "API key as a Bearer token. Never declare media real or fake without a "
        "completed detection result; always report the label with its score."
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


async def _poll(api_key: str, path: str, max_wait_seconds: float) -> Any:
    budget = _clamp(max_wait_seconds, 1, MAX_WAIT_CEILING, 120)
    elapsed, delay = 0.0, 2.0
    last = await _request(api_key, "GET", path)
    while True:
        status = str(_item(last).get("status") or "").lower()
        if not status or status in TERMINAL_STATUSES or elapsed >= budget:
            return last
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
