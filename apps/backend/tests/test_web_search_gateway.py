from __future__ import annotations

import httpx

from app.core.config import Settings
from app.services.web_search_gateway import DashScopeWebSearchGateway


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
