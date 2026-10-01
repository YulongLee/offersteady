"""Isolated realtime TTS transport; no session cache, audio persistence or billing."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
from collections.abc import AsyncIterator, Callable
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
        prompt = "ai/prompts/mock-interview/en/tts.txt" if settings.product_edition == "global" else "ai/prompts/mock-interview/tts.txt"
        self._instructions = (REPO_ROOT / prompt).read_text(encoding="utf-8").strip()

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        if not text.strip() or len(text) > self.max_text_characters:
            raise MockSpeechUnavailable("朗读文本不可用。")
        key = self.settings.mock_interview_tts_api_key or self.settings.chat_qwen_api_key
        endpoint = urlsplit(self.settings.global_mock_interview_tts_ws_url
            if self.settings.product_edition == "global" else self.settings.mock_interview_tts_ws_url)
        if not key or endpoint.scheme != "wss" or endpoint.username or endpoint.password:
            raise MockSpeechUnavailable("模拟面试语音尚未配置。")
        query = dict(parse_qsl(endpoint.query))
        query["model"] = self.settings.mock_interview_tts_model
        url = urlunsplit(endpoint._replace(query=urlencode(query)))

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
                        await send(socket, "session.update", session={
                            "voice": self.settings.mock_interview_tts_voice,
                            "mode": "commit", "language_type": "English" if self.settings.product_edition == "global" else "Chinese",
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
