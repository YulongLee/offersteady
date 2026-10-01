"""Existing companion wire protocol routed exclusively to mock capture."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
from collections import deque
from time import monotonic

import anyio
from fastapi import WebSocketDisconnect
from pydantic import ValidationError

from app.core.errors import DomainRequestError
from app.schemas.realtime_speech import RealtimeFrameRequest

MAX_HEADER = 64 * 1024
MAX_PCM = 256 * 1024


def decode_frame(message, media):
    if message.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    if media == "binary-v1":
        raw = message.get("bytes")
        if not isinstance(raw, bytes) or len(raw) < 6:
            raise ValueError("binary frame required")
        size = int.from_bytes(raw[:4], "big")
        if not 2 <= size <= MAX_HEADER or size + 4 > len(raw) or len(raw) - size - 4 > MAX_PCM:
            raise ValueError("invalid frame size")
        header = json.loads(raw[4:4 + size])
        if not isinstance(header, dict) or "audioBase64" in header:
            raise ValueError("invalid header")
        return RealtimeFrameRequest.model_validate({**header, "audioBase64": ""}), raw[4 + size:]
    raw = message.get("text")
    if not isinstance(raw, str) or len(raw) > MAX_HEADER + MAX_PCM * 2:
        raise ValueError("invalid json frame")
    frame = RealtimeFrameRequest.model_validate(json.loads(raw))
    pcm = base64.b64decode(frame.audio_base64, validate=True)
    if len(pcm) > MAX_PCM:
        raise ValueError("audio too large")
    return frame, pcm


async def serve_legacy_microphone(websocket, token, protocol, media):
    # Imported lazily: the regular realtime router must not instantiate mock
    # services or migrations for an ordinary interview.
    from app.modules.mock_interview import require_mock_runtime
    runtime = None
    entry = None
    failure = None
    try:
        if protocol != "2.0" or media not in ("binary-v1", "json-base64"):
            raise ValueError("unsupported protocol")
        runtime = require_mock_runtime()
        entry = await runtime.legacy.connect(token)
        await websocket.send_json({"kind": "connection-state", "payload": {
            "publisherId": entry.publisher.publisher_id, "status": "connected", "sourceKind": "microphone",
            "transport": "websocket-v2-multiplexed", "protocolVersion": "2.0", "channels": ["microphone", "system"],
            "mediaMode": media, "resumeOffsets": {k: v - 1 for k, v in entry.expected.items()},
            "resumeSourceGenerations": entry.generations}})
        await runtime.publish(runtime.controllers[entry.publisher.session_id])
        arrivals = deque()
        next_check = monotonic() + 5
        while not entry.revoked:
            if monotonic() >= next_check:
                await runtime.legacy.validate(entry)
                next_check = monotonic() + 5
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=1)
            except asyncio.TimeoutError:
                continue
            now = monotonic()
            while arrivals and arrivals[0] <= now - 1:
                arrivals.popleft()
            if len(arrivals) >= 40:
                raise ValueError("audio rate exceeded")
            arrivals.append(now)
            frame, pcm = decode_frame(message, media)
            await websocket.send_json(await runtime.legacy.accept(entry, frame, pcm))
    except WebSocketDisconnect:
        pass
    except (ValueError, ValidationError, binascii.Error):
        failure = "收音数据无效，已暂停，请重新连接助手。"
    except DomainRequestError as exc:
        failure = exc.message
    except asyncio.CancelledError:
        raise
    except Exception:
        failure = "收音暂时不可用，已暂停，可重新连接后继续本题。"
    finally:
        # ASGI disconnect cancellation must not interrupt ASR/meter cleanup.
        with anyio.CancelScope(shield=True):
            try:
                if entry and runtime:
                    await runtime.legacy.disconnect(entry, failure)
            finally:
                try:
                    if failure:
                        await websocket.send_json({"kind": "connection-rejected", "payload": {"message": failure}})
                    await websocket.close(code=1008 if failure else 1000)
                except (RuntimeError, WebSocketDisconnect, OSError):
                    pass
