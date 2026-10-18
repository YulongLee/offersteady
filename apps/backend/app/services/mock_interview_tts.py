"""Isolated realtime TTS transport; no session cache, audio persistence or billing."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
from collections.abc import AsyncIterator, Callable
from contextlib import aclosing
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.core.config import REPO_ROOT, Settings


class MockSpeechUnavailable(RuntimeError):
    """Safe public error: deliberately never carries the provider response or key."""


class MockInterviewTts:
    sample_rate = 24_000
    max_audio_bytes = sample_rate * 2 * 90
    max_text_characters = 800

    def __init__(self, settings: Settings, *, connector: Callable = connect) -> None:
        self.settings = settings
        self._connector = connector
        self._slots = asyncio.Semaphore(settings.mock_interview_provider_concurrency)
        self._instructions = (REPO_ROOT / "ai/prompts/mock-interview/tts.txt").read_text(encoding="utf-8").strip()

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        if not text.strip() or len(text) > self.max_text_characters:
            raise MockSpeechUnavailable("朗读文本不可用。")
        key = self.settings.mock_interview_tts_api_key or self.settings.chat_qwen_api_key
        endpoint = urlsplit(self.settings.mock_interview_tts_ws_url)
        if not key or endpoint.scheme != "wss" or endpoint.username or endpoint.password:
            raise MockSpeechUnavailable("模拟面试语音尚未配置。")
        audio_plus = self.settings.mock_interview_tts_model == "qwen-audio-3.0-tts-plus"
        if audio_plus and (endpoint.path != "/api-ws/v1/inference" or endpoint.query or endpoint.fragment):
            raise MockSpeechUnavailable("模拟面试语音端点配置不匹配。")
        query = dict(parse_qsl(endpoint.query))
        query["model"] = self.settings.mock_interview_tts_model
        url = urlunsplit(endpoint if audio_plus else endpoint._replace(query=urlencode(query)))

        async def send(socket, kind: str, **payload) -> None:
            await socket.send(json.dumps({"event_id": uuid4().hex, "type": kind, **payload}))

        # Waiting for capacity is also bounded. Cancellation unwinds both contexts.
        try:
            async with asyncio.timeout(self.settings.mock_interview_provider_timeout_seconds):
                async with self._slots:
                    async with self._connector(
                        url, additional_headers={"Authorization": f"Bearer {key}"},
                        open_timeout=8, close_timeout=2, max_size=512 * 1024, max_queue=4,
                    ) as socket:
                        if audio_plus:
                            # Explicitly close the inner generator when the caller
                            # ends/replays after a yielded chunk, not just on errors.
                            async with aclosing(self._stream_audio_plus(socket, text)) as audio:
                                async for chunk in audio:
                                    yield chunk
                            return
                        await send(socket, "session.update", session={
                            "voice": self.settings.mock_interview_tts_voice,
                            "mode": "commit", "language_type": "Chinese",
                            "response_format": "pcm", "sample_rate": self.sample_rate,
                            "instructions": self._instructions, "optimize_instructions": False,
                        })
                        submitted = False
                        total = 0
                        async for raw in socket:
                            event = json.loads(raw)
                            kind = event.get("type")
                            if kind == "error":
                                raise MockSpeechUnavailable("朗读服务暂时不可用，可重试或按文字继续。")
                            if kind == "session.updated" and not submitted:
                                submitted = True
                                await send(socket, "input_text_buffer.append", text=text)
                                await send(socket, "input_text_buffer.commit")
                                await send(socket, "session.finish")
                            elif kind == "response.audio.delta":
                                if not submitted:
                                    raise MockSpeechUnavailable("朗读协议异常。")
                                chunk = base64.b64decode(event.get("delta", ""), validate=True)
                                total += len(chunk)
                                if total > self.max_audio_bytes:
                                    raise MockSpeechUnavailable("朗读超过时长限制。")
                                if chunk:
                                    yield chunk
                            elif kind == "response.done":
                                status = event.get("response", {}).get("status")
                                if status not in (None, "completed"):
                                    raise MockSpeechUnavailable("朗读未完成，可重试。")
                            elif kind == "session.finished":
                                if not submitted or total == 0:
                                    raise MockSpeechUnavailable("朗读未返回有效音频。")
                                return
                        raise MockSpeechUnavailable("朗读连接提前中断，可重试。")
        except MockSpeechUnavailable:
            raise
        except ConnectionClosed as exc:
            reason = exc.rcvd.reason if exc.rcvd else ""
            if reason == "Model access denied.":
                raise MockSpeechUnavailable("当前百炼业务空间未获此语音模型调用权限，请联系管理员授权。") from None
            raise MockSpeechUnavailable("朗读连接中断，可重试或按文字继续。") from None
        except WebSocketException:
            raise MockSpeechUnavailable("无法连接朗读服务，可重试或按文字继续。") from None
        except (TimeoutError, OSError, ValueError, binascii.Error):
            raise MockSpeechUnavailable("朗读超时或连接异常，可重试或按文字继续。") from None

    async def _stream_audio_plus(self, socket, text: str) -> AsyncIterator[bytes]:
        """Inference duplex protocol; the outer context owns timeout and socket."""
        task_id = str(uuid4())

        async def send(action: str, payload: dict) -> None:
            await socket.send(json.dumps({
                "header": {"action": action, "task_id": task_id, "streaming": "duplex"},
                "payload": payload,
            }))

        await send("run-task", {
            "task_group": "audio", "task": "tts", "function": "SpeechSynthesizer",
            "model": self.settings.mock_interview_tts_model,
            "parameters": {
                "text_type": "PlainText", "voice": self.settings.mock_interview_tts_voice,
                "format": "pcm", "sample_rate": self.sample_rate,
                "volume": 50, "rate": 1.0, "pitch": 1.0, "enable_ssml": False,
                "instruction": self._instructions,
            },
            "input": {},
        })
        started = False
        total = 0
        pending = b""
        async for raw in socket:
            if isinstance(raw, bytes):
                if not started:
                    raise MockSpeechUnavailable("朗读协议异常。")
                total += len(raw)
                if total > self.max_audio_bytes:
                    raise MockSpeechUnavailable("朗读超过时长限制。")
                # PCM samples can cross frame boundaries; retain at most one byte.
                chunk = pending + raw
                end = len(chunk) - len(chunk) % 2
                pending = chunk[end:]
                if end:
                    yield chunk[:end]
                continue
            event = json.loads(raw)
            header = event.get("header") if isinstance(event, dict) else None
            if not isinstance(header, dict) or header.get("task_id") != task_id:
                raise MockSpeechUnavailable("朗读协议异常。")
            kind = header.get("event")
            if kind == "task-failed":
                raise MockSpeechUnavailable("朗读服务暂时不可用，可重试或按文字继续。")
            if kind == "task-started":
                if started:
                    raise MockSpeechUnavailable("朗读协议异常。")
                started = True
                await send("continue-task", {"input": {"text": text}})
                await send("finish-task", {"input": {}})
            elif kind == "result-generated":
                payload = event.get("payload")
                output = payload.get("output") if isinstance(payload, dict) else None
                if not started or not isinstance(output, dict) or output.get("type") not in (
                    "sentence-begin", "sentence-synthesis", "sentence-end",
                ):
                    raise MockSpeechUnavailable("朗读协议异常。")
            elif kind == "task-finished":
                if not started or total == 0 or pending:
                    raise MockSpeechUnavailable("朗读未返回有效音频。")
                return
            else:
                raise MockSpeechUnavailable("朗读协议异常。")
        raise MockSpeechUnavailable("朗读连接提前中断，可重试。")
