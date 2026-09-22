from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.services.web_search_gateway import DashScopeWebSearchGateway


@pytest.mark.parametrize("outcome", ["success", "timeout", "rejected"])
def test_web_search_explicitly_disables_deep_thinking(outcome: str) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        assert payload["reasoning"] == {"effort": "none"}
        assert "enable_thinking" not in payload
        assert payload["tools"] == [{"type": "web_search"}]
        assert payload["model"] == "deepseek-v4.1-flash"
        assert payload["max_output_tokens"] == 1400
        if outcome == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if outcome == "rejected":
            return httpx.Response(400, json={"error": {"code": "synthetic_rejection"}})
        return httpx.Response(200, json={"output_text": "合成联网详细回答。"})

    settings = Settings(
        _env_file=None,
        web_search_enabled=True,
        web_search_responses_base_url="https://dashscope.example/v1",
        web_search_api_key="synthetic-test-key",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = DashScopeWebSearchGateway(settings, http_client=client).answer(
            question="如何核验公开技术信息？",
            system_prompt="只使用可核验的公开信息。",
            user_prompt="给出详细说明。",
            model="deepseek-v4.1-flash",
            max_tokens=1400,
            language="中文",
        )

    assert len(requests) == 1
    assert result.status == ("succeeded" if outcome == "success" else "fallback")
    if outcome == "timeout":
        assert result.safe_error_code == "web_search_provider_unavailable"
    elif outcome == "rejected":
        assert result.safe_error_code == "web_search_provider_rejected"


def test_web_search_gateway_extracts_answer_and_sources() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/responses")
        payload = request.content.decode("utf-8")
        assert '"web_search"' in payload
        return httpx.Response(200, json={
            "output_text": "公开资料显示，示例技术在该场景中通常用于降低延迟。",
            "output": [{"content": [{
                "type": "output_text",
                "annotations": [{"title": "官方文档", "url": "https://example.com/docs", "snippet": "官方说明"}],
            }]}],
        })

    settings = Settings(
        web_search_enabled=True,
        web_search_responses_base_url="https://dashscope.example/v1",
        web_search_api_key="test-key",
    )
    gateway = DashScopeWebSearchGateway(settings, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = gateway.answer(
        question="什么是示例技术？",
        system_prompt="保持专业。",
        user_prompt="回答问题。",
        model="deepseek-v4.1-flash",
        max_tokens=400,
        language="中文",
    )
    assert result.status == "succeeded"
    assert result.answer_text.startswith("公开资料")
    assert result.sources[0].url == "https://example.com/docs"


def test_web_search_gateway_falls_back_without_provider_config() -> None:
    gateway = DashScopeWebSearchGateway(Settings(web_search_enabled=False))
    result = gateway.answer(
        question="当前问题",
        system_prompt="",
        user_prompt="",
        model="deepseek-v4.1-flash",
        max_tokens=400,
        language="中文",
    )
    assert result.status == "unavailable"
    assert result.safe_error_code == "web_search_not_configured"


def test_web_search_gateway_extracts_responses_api_search_call_sources() -> None:
    text, sources = DashScopeWebSearchGateway._extract(
        body={
            "output": [{
                "type": "web_search_call",
                "action": {
                    "type": "search",
                    "query": "示例问题",
                    "sources": [
                        {"type": "url", "url": "https://example.com/first"},
                        {"type": "url", "url": "https://example.com/second"},
                    ],
                },
            }],
        },
        retrieved_at_ms=123,
    )

    assert text == ""
    assert [source.url for source in sources] == [
        "https://example.com/first",
        "https://example.com/second",
    ]
    assert sources[0].title == "example.com"
