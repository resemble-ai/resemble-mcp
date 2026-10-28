"""Real MCP -> connector -> live Resemble smoke test; NOT a Cowork host test.

Only submit purpose-made, non-sensitive test fixtures. Results are not benchmarks.
Credentials stay in environment variables; reports exclude content and tokens.
"""
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(args):
    token = os.environ.get("RESEMBLE_ACCESS_TOKEN") or os.environ.get("RESEMBLE_API_KEY")
    if not token:
        raise SystemExit("Set RESEMBLE_ACCESS_TOKEN (OAuth) or RESEMBLE_API_KEY (API smoke only).")
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "endpoint": args.endpoint,
              "credential_type": "oauth" if os.environ.get("RESEMBLE_ACCESS_TOKEN") else "api_key",
              "cowork_host_test": False, "checks": [], "jobs": []}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(report, indent=2) + "\n")

    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=28) as http:
        async with streamable_http_client(args.endpoint, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                report["checks"].append({"name": "initialize_and_discover", "passed": len(tools.tools) == 7,
                                          "tools": [t.name for t in tools.tools]})
                print("Connected and discovered", len(tools.tools), "tools", flush=True)

                async def call(name, arguments):
                    start = time.monotonic()
                    result = await session.call_tool(name, arguments)
                    elapsed = round(time.monotonic() - start, 3)
                    if result.isError:
                        raise RuntimeError(name + ": " + "; ".join(c.text for c in result.content if hasattr(c, "text")))
                    report["checks"].append({"name": name, "elapsed_seconds": elapsed, "passed": elapsed < 30})
                    save()
                    return result.structuredContent or json.loads(result.content[0].text)

                async def poll(name, arguments):
                    deadline = time.monotonic() + args.wait_seconds
                    delay = 2
                    while True:
                        result = await call(name, arguments)
                        if result.get("status") in ("completed", "failed", "error", "cancelled"):
                            return result
                        if time.monotonic() >= deadline:
                            return result
                        await asyncio.sleep(delay)
                        delay = min(10, delay + 3)

                async def media(label, arguments):
                    submitted = await call("submit_media_detection", arguments)
                    job = {"kind": label, "uuid": submitted["uuid"], "status": submitted["status"]}
                    report["jobs"].append(job)
                    save()
                    print(label, "submitted", job["uuid"], flush=True)
                    result = await poll("get_media_detection", {"uuid": job["uuid"]})
                    job.update({"status": result["status"], "completed": result.get("completed"),
                                "modalities": {k: {f: result[k][f] for f in ("label", "score", "aggregated_score") if f in result[k]}
                                               for k in ("metrics", "image_metrics", "video_metrics") if isinstance(result.get(k), dict)}})
                    save()
                    print(label, "finished:", job["status"], flush=True)
                    return job

                try:
                    last_completed = None
                    signal_inputs = []
                    if args.signal:
                        signal_inputs.extend([
                            ("signal:benign_text", {"text": "The community garden opens at nine on Saturday. Volunteers will plant tomatoes and water the seedlings. Bring gardening gloves and a reusable water bottle. This is a synthetic integration test."}),
                            ("signal:synthetic_fraud", {"text": "I am your chief executive. I need you to urgently wire fifty thousand dollars to a new account before close of business. Keep this confidential and do not call me or the finance team to verify. This request overrides the usual approval process."}),
                        ])
                    for filename in args.signal_file:
                        path = Path(filename)
                        signal_inputs.append(("signal:attachment:" + path.suffix,
                            {"file": base64.b64encode(path.read_bytes()).decode(), "filename": path.name}))
                    for label, arguments in signal_inputs:
                        result = await call("score_signal_content", arguments)
                        job = {"kind": label, "id": result.get("id"), "status": result.get("status"),
                               "completed": result.get("assessment_available") is True,
                               "verdict": result.get("verdict"), "top_category": result.get("top_category"),
                               "coverage": result.get("coverage")}
                        report["jobs"].append(job)
                        save()
                        print(label, "finished:", job["status"], "id:", job["id"], flush=True)
                    if args.detect_uuid:
                        result = await poll("get_media_detection", {"uuid": args.detect_uuid})
                        job = {"kind": "existing_media", "uuid": args.detect_uuid, "status": result["status"], "completed": result.get("completed")}
                        report["jobs"].append(job)
                        if job["completed"]:
                            last_completed = job
                    for filename in args.file:
                        path = Path(filename)
                        job = await media("attachment:" + path.suffix, {"file": base64.b64encode(path.read_bytes()).decode(), "filename": path.name})
                        if job["completed"]:
                            last_completed = job
                    if args.url:
                        job = await media("public_url", {"url": args.url})
                        if job["completed"]:
                            last_completed = job
                    if args.text:
                        text = ("This passage was generated specifically to test the Resemble Copilot integration. "
                                "It contains no private information and makes no claim about a real person. "
                                "The test checks whether a text analysis job can be submitted, retrieved, and reported "
                                "through the connector without confusing pending processing with a completed prediction.")
                        submitted = await call("submit_text_detection", {"text": text})
                        job = {"kind": "text", "uuid": submitted["uuid"], "status": submitted["status"]}
                        report["jobs"].append(job)
                        save()
                        print("Text submitted", job["uuid"], flush=True)
                        result = await poll("get_text_detection", {"uuid": job["uuid"]})
                        job.update({k: result.get(k) for k in ("status", "completed", "prediction", "confidence")})
                        save()
                        print("Text finished:", job["status"], flush=True)
                    if args.question and last_completed:
                        detect_uuid = last_completed["uuid"]
                        submitted = await call("submit_detection_question", {"detect_uuid": detect_uuid, "query": "Summarize the returned detector evidence and its limitations in two sentences."})
                        job = {"kind": "question", "detect_uuid": detect_uuid, "uuid": submitted["uuid"], "status": submitted["status"]}
                        report["jobs"].append(job)
                        save()
                        result = await poll("get_detection_answer", {"detect_uuid": detect_uuid, "question_uuid": job["uuid"]})
                        job.update({"status": result["status"], "completed": result.get("completed"), "answer_present": bool(result.get("answer"))})
                        save()
                        print("Question finished:", job["status"], flush=True)
                except Exception as error:
                    report["error"] = str(error).replace(token, "[redacted]")
                    save()
                    raise
    report["passed"] = bool(report["jobs"]) and all(j.get("completed") for j in report["jobs"]) and all(c["passed"] for c in report["checks"])
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    print("Live API smoke:", "PASS" if report["passed"] else "INCOMPLETE", "— Cowork host remains untested", flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", default="http://127.0.0.1:8879/cowork/mcp")
    p.add_argument("--file", action="append", default=[])
    p.add_argument("--url")
    p.add_argument("--text", action="store_true")
    p.add_argument("--question", action="store_true")
    p.add_argument("--signal", action="store_true", help="Score benign and synthetic fraud text fixtures; consumes Signal credits.")
    p.add_argument("--signal-file", action="append", default=[], help="Score a purpose-made media fixture with Signal.")
    p.add_argument("--detect-uuid", help="Resume an existing detection, optionally to ask a question; does not resubmit media.")
    p.add_argument("--wait-seconds", type=int, default=600)
    p.add_argument("--output", default="copilot/evidence/live-smoke.json")
    asyncio.run(run(p.parse_args()))
