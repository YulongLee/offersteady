"""Opt-in synthetic permission checks, no application/database writes or audio files.

Can run on stdin in the existing Global container without installing new code.
Credentials remain inside that process. Never print raw responses/exceptions.
"""
import argparse
import asyncio
import base64
import json
import re
from time import monotonic
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings


def safe_code(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value) else "provider_rejected"


async def tts(settings):
    started = monotonic()
    endpoint = getattr(settings, "global_mock_interview_tts_ws_url", "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime")
    key = getattr(settings, "mock_interview_tts_api_key", None) or settings.chat_qwen_api_key
    model = getattr(settings, "mock_interview_tts_model", "qwen3-tts-instruct-flash-realtime")
    result = {"kind": "tts", "host": urlsplit(endpoint).hostname, "model": model, "audio_bytes": 0}
    try:
        async with asyncio.timeout(25):
            async with connect(endpoint + "?model=" + model, additional_headers={"Authorization": "Bearer " + key},
                               open_timeout=8, close_timeout=2, max_size=512*1024, max_queue=4) as socket:
                async def send(kind, **body):
                    await socket.send(json.dumps({"type": kind, "event_id": uuid4().hex, **body}))
                await send("session.update", session={"mode": "commit", "voice": "Cherry", "language_type": "English",
                    "response_format": "pcm", "sample_rate": 24000,
                    "instructions": "Speak English as a calm, professional interviewer.", "optimize_instructions": False})
                sent = False
                async for raw in socket:
                    event = json.loads(raw)
                    if event.get("type") == "session.updated" and not sent:
                        sent = True
                        await send("input_text_buffer.append", text="Tell me about a project you worked on.")
                        await send("input_text_buffer.commit")
                        await send("session.finish")
                    elif event.get("type") == "response.audio.delta":
                        result["audio_bytes"] += len(base64.b64decode(event.get("delta", ""), validate=True))
                        if "first_audio_seconds" not in result:
                            result["first_audio_seconds"] = round(monotonic()-started, 3)
                        if result["audio_bytes"] > 24000*2*30:
                            raise ValueError("bounded synthetic probe")
                    elif event.get("type") == "error":
                        result["status"] = safe_code(event.get("error", {}).get("code"))
                        return result
                    elif event.get("type") == "session.finished":
                        result["status"] = "passed" if result["audio_bytes"] else "no_audio"
                        return result
                result["status"] = "early_close"
    except ConnectionClosed as error:
        result["status"] = "model_access_denied" if error.rcvd and error.rcvd.reason == "Model access denied." else "connection_closed"
    except Exception as error:
        result["status"] = type(error).__name__
    finally:
        result["seconds"] = round(monotonic()-started, 3)
    return result


async def search(settings):
    started = monotonic()
    base = getattr(settings, "web_search_responses_base_url", None) or settings.chat_qwen_base_url
    key = getattr(settings, "web_search_api_key", None) or settings.chat_qwen_api_key
    result = {"kind": "web_search", "host": urlsplit(base).hostname, "model": settings.chat_qwen_model,
              "explicit_search_endpoint": bool(getattr(settings, "web_search_responses_base_url", None))}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=5), follow_redirects=False) as client:
            response = await client.post(base.rstrip("/") + "/responses", headers={"Authorization": "Bearer " + key}, json={
                "model": settings.chat_qwen_model,
                "input": "Search the official Python website and identify its current stable release. Give one source and one sentence.",
                "tools": [{"type": "web_search"}], "reasoning": {"effort": "none"}, "max_output_tokens": 256, "temperature": .2,
            })
            result["http_status"] = response.status_code
            try:
                body = response.json()
            except ValueError:
                body = {}
            if response.is_success:
                output = body.get("output", [])
                result["search_calls"] = sum(item.get("type") == "web_search_call" for item in output)
                result["source_count"] = sum(len(item.get("action", {}).get("sources", [])) for item in output if item.get("type") == "web_search_call")
                result["text_characters"] = sum(len(part.get("text", "")) for item in output if item.get("type") == "message" for part in item.get("content", []))
                result["status"] = "passed" if result["search_calls"] and result["text_characters"] else "unverified_search"
            else:
                error = body.get("error", {})
                result["status"] = safe_code(error.get("code") if isinstance(error, dict) else None)
    except Exception as error:
        result["status"] = type(error).__name__
    result["seconds"] = round(monotonic()-started, 3)
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        parser.error("Explicit --run required: calls existing Global providers with synthetic inputs")
    settings = get_settings()
    if settings.product_edition != "global":
        raise SystemExit("Global edition required")
    # Sequential to keep this diagnostic negligible alongside real traffic.
    print(json.dumps(await tts(settings)), flush=True)
    print(json.dumps(await search(settings)), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
