from __future__ import annotations

import json
import logging
import re
from json import JSONDecodeError
from time import time
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.core.logging import log_event
from app.ports.web_search import WebSearchAnswer, WebSearchGatewayPort, WebSearchSource


def _now_ms() -> int:
    return int(time() * 1000)


def _safe_query(value: str) -> str:
    value = " ".join(value.replace("\x00", " ").split())
    return value[:500].strip()


def _safe_url(value: object) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url[:2000]


class DashScopeWebSearchGateway(WebSearchGatewayPort):
    """Server-side web answer adapter for DashScope Responses API.

    The provider is intentionally opt-in. An empty responses base URL makes the
    gateway unavailable and lets ChatService fall back to local retrieval.
    """

    def __init__(self, settings: Settings, *, http_client: httpx.Client | None = None, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self._http_client = http_client
        self._logger = logger or logging.getLogger(__name__)

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=httpx.Timeout(
                    max(0.5, self.settings.web_search_timeout_seconds),
                    connect=min(2.0, max(0.5, self.settings.web_search_timeout_seconds)),
                )
            )
        return self._http_client

    def answer(
        self,
        *,
        question: str,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        language: str,
    ) -> WebSearchAnswer:
        started_at = _now_ms()
        log_status = "unavailable"
        base_url = (self.settings.web_search_responses_base_url or "").strip().rstrip("/")
        api_key = (self.settings.web_search_api_key or self.settings.chat_qwen_api_key or "").strip()
        safe_question = _safe_query(question)
        if not self.settings.web_search_enabled or not base_url or not api_key or not safe_question:
            return WebSearchAnswer(
                answer_text="",
                status="unavailable",
                provider="dashscope-responses",
                duration_ms=max(0, _now_ms() - started_at),
                safe_error_code="web_search_not_configured",
            )
        language_label = language or "the selected interview language"
        prompt = (
            f"Answer the interview question in {language_label}. Use web search for current or factual context. "
            "Do not invent candidate experience, employers, metrics, or personal history. "
            "Clearly distinguish web facts from the candidate's provided evidence and recommendations. "
            "Keep the answer professional and concise.\n\n"
            f"{user_prompt}"
        )
        max_context_characters = max(1, min(12000, int(self.settings.web_search_max_context_characters)))
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt[:max_context_characters]},
            ],
            "tools": [{"type": "web_search"}],
            "max_output_tokens": max(256, min(max_tokens, 4096)),
            "temperature": 0.2,
        }
        try:
            response = self._client().post(
                f"{base_url}/responses",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if response.status_code in {401, 403}:
                return self._failure(started_at, "web_search_auth_failed")
            if response.status_code == 429:
                return self._failure(started_at, "web_search_rate_limited")
            if response.status_code >= 400:
                return self._failure(started_at, "web_search_provider_rejected")
            body = response.json()
            answer_text, sources = self._extract(body=body, retrieved_at_ms=_now_ms())
            if not answer_text:
                return self._failure(started_at, "web_search_empty_result")
            log_status = "succeeded"
            return WebSearchAnswer(
                answer_text=answer_text,
                sources=sources[: max(1, self.settings.web_search_max_sources)],
                status="succeeded",
                provider="dashscope-responses",
                duration_ms=max(0, _now_ms() - started_at),
            )
        except (httpx.HTTPError, JSONDecodeError, ValueError, TypeError):
            return self._failure(started_at, "web_search_provider_unavailable")
        finally:
            log_event(
                self._logger,
                logging.INFO,
                settings=self.settings,
                event="web_search.completed",
                feature="live-answer",
                action="web-search",
                duration_ms=max(0, _now_ms() - started_at),
                status=log_status,
            )

    def _failure(self, started_at: int, code: str) -> WebSearchAnswer:
        return WebSearchAnswer(
            answer_text="",
            status="fallback",
            provider="dashscope-responses",
            duration_ms=max(0, _now_ms() - started_at),
            safe_error_code=code,
        )

    @classmethod
    def _extract(cls, *, body: object, retrieved_at_ms: int) -> tuple[str, list[WebSearchSource]]:
        if not isinstance(body, dict):
            return "", []
        text = str(body.get("output_text") or "").strip()
        sources: list[WebSearchSource] = []
        output = body.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
                    if not isinstance(content, dict):
                        continue
                    if not text and content.get("type") in {"output_text", "text"}:
                        text = str(content.get("text") or "").strip()
                    annotations = content.get("annotations")
                    if isinstance(annotations, list):
                        for annotation in annotations:
                            if not isinstance(annotation, dict):
                                continue
                            url = _safe_url(annotation.get("url"))
                            if not url:
                                continue
                            sources.append(WebSearchSource(
                                title=str(annotation.get("title") or urlparse(url).netloc)[:240],
                                url=url,
                                snippet=str(annotation.get("snippet") or "")[:800],
                                retrieved_at_ms=retrieved_at_ms,
                            ))
        unique: list[WebSearchSource] = []
        seen: set[str] = set()
        for source in sources:
            if source.url in seen:
                continue
            seen.add(source.url)
            unique.append(source)
        return text, unique
