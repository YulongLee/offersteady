"""Synthetic-only real adapter probe. No application sessions, fees or audio files."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
from time import monotonic

sys.path.insert(0, "/app/apps/backend")

from websockets.asyncio.client import connect
from websockets.protocol import State
from app.core.config import Settings
from app.services.mock_interview_tts import MockInterviewTts


async def verify(rows):
    settings = Settings()
    assert settings.product_edition == "cn"
    assert settings.mock_interview_tts_model == "qwen-audio-3.0-tts-plus"
    assert settings.mock_interview_tts_voice == "longanhuan_v3.6"
    assert settings.mock_interview_tts_ws_url == "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    sockets = []

    @asynccontextmanager
    async def tracked(*args, **kwargs):
        async with connect(*args, **kwargs) as socket:
            sockets.append(socket)
            yield socket

    service = MockInterviewTts(settings, connector=tracked)
    results = []
    for row in rows:
        assert row["model"] == settings.mock_interview_tts_model and row["voice"] == settings.mock_interview_tts_voice
        started = monotonic()
        total = chunks = 0
        non_silent = False
        first = None
        async for pcm in service.stream(row["text"]):
            if first is None:
                first = monotonic() - started
            assert len(pcm) % 2 == 0
            total += len(pcm)
            chunks += 1
            non_silent |= any(pcm)
        assert total > 48000 and total <= service.max_audio_bytes and non_silent
        assert sockets[-1].state == State.CLOSED and service._slots._value == settings.mock_interview_provider_concurrency
        result = {"id": row["id"], "passed": True, "audioBytes": total, "chunks": chunks,
                  "audioSeconds": round(total / 48000, 3), "firstAudioSeconds": round(first, 3),
                  "seconds": round(monotonic() - started, 3), "connectionClosed": True, "nonSilent": non_silent}
        results.append(result)
        print(json.dumps(result), flush=True)
    # End/replay while the provider is still sending: close the actual adapter.
    stream = service.stream(rows[0]["text"])
    try:
        assert await anext(stream)
    finally:
        await stream.aclose()
    assert sockets[-1].state == State.CLOSED and service._slots._value == settings.mock_interview_provider_concurrency
    assert len(sockets) == len(rows) + 1
    return {"passed": True, "model": settings.mock_interview_tts_model, "voice": settings.mock_interview_tts_voice,
            "checks": results, "cancelPassed": True, "allConnectionsClosed": True,
            "syntheticOnly": True, "productSessionsCreated": 0, "audioPersisted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", required=True)
    args = parser.parse_args()
    try:
        rows = [json.loads(line) for line in Path(args.fixtures).read_text().splitlines() if line.strip()]
        assert len(rows) == 2
        print(json.dumps(asyncio.run(verify(rows))), flush=True)
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
