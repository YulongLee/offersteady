"""Offline candidate contracts; passing these tests does not prove provider access.

Every HTTP request is intercepted by MockTransport. No API key, production data,
database, interview session or wallet is used by this suite.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json

import httpx
from PIL import Image
import pytest

from app.core.config import REPO_ROOT, Settings
from app.ports.chat import PromptBuildResult, PromptConfig
from app.ports.screenshot_answer import PreparedScreenshotImage
from app.services.chat_service import QwenCompatibleGateway
from app.services.cn_resume_optimizer_provider import CNResumeOptimizerProvider, ResumeProviderError
from app.services.screenshot_answer_service import OpenAICompatibleVisionGateway


MODEL = "deepseek-v4.1-flash-1017"
EVALS = [json.loads(line) for line in (REPO_ROOT / "ai/evals/model-v41-flash-1017.jsonl").read_text().splitlines() if line.strip()]
RESUME_CASES = [case for case in EVALS if case["operation"] == "resume"]


def settings(**updates) -> Settings:
    values = dict(
        environment="test", product_edition="cn",
        chat_qwen_model="synthetic-original-shared", chat_quick_model="synthetic-original-quick",
        chat_detail_model="synthetic-original-detail", screenshot_vision_model="synthetic-original-vision",
        chat_qwen_api_key="synthetic-only", chat_qwen_base_url="https://text.synthetic.invalid/v1",
        screenshot_vision_api_key="synthetic-only", screenshot_vision_base_url="https://vision.synthetic.invalid/v1",
    )
    values.update(updates)
    return Settings(_env_file=None, **values)


def prompt(template_id: str) -> PromptBuildResult:
    return PromptBuildResult(
        system_prompt="仅根据合成证据回答，不编造经历。", user_prompt="合成问题：如何实现请求幂等？",
        rendered_prompt="synthetic-only", prompt_config=PromptConfig(template_id, "synthetic-1017", 1),
        retrieval_excerpt_count=0,
    )


def sse(text: str, *, finish_reason: str = "stop") -> bytes:
    events = [
        {"choices": [{"delta": {"reasoning_content": "synthetic-hidden-reasoning"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": text}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": finish_reason}]},
    ]
    return ("".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in events) + "data: [DONE]\n\n").encode()


@pytest.mark.parametrize(("template", "field", "budget"), [
    ("interview-chat-quick", "chat_quick_model", 420),
    ("interview-chat-en-quick", "chat_quick_model", 420),
    ("interview-chat-continuation-quick", "chat_quick_model", 900),
    ("interview-chat-detail", "chat_detail_model", 1400),
    ("interview-chat-continuation-detail", "chat_detail_model", 900),
    ("interview-chat-generic", "chat_qwen_model", 1400),
])
@pytest.mark.parametrize("stream", [False, True])
def test_candidate_routes_only_the_selected_text_stage(template, field, budget, stream, monkeypatch):
    requests = []
    text = "<normalized_question>如何实现请求幂等？</normalized_question>\n使用唯一键约束。" if field == "chat_quick_model" else "使用唯一键约束，并测试并发重复请求。"

    def handle(request):
        requests.append(json.loads(request.content))
        assert str(request.url) == "https://text.synthetic.invalid/v1/chat/completions"
        if stream:
            return httpx.Response(200, content=sse(text), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"choices": [{"message": {"content": text}, "finish_reason": "stop"}]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        config = settings(**{field: MODEL})
        gateway = QwenCompatibleGateway(config, http_client=client)
        monkeypatch.setattr(gateway, "_should_use_remote_gateway", lambda: True)
        if stream:
            chunks = list(gateway.stream_generate(question="合成问题", prompt=prompt(template), attempt=0))
            assert "".join(chunk.text for chunk in chunks) == text
            assert chunks[-1].is_final and chunks[-1].provider_finish_reason == "stop"
        else:
            result = gateway.generate(question="合成问题", prompt=prompt(template), stream=False, attempt=0)
            assert result.final_text == text and result.model_name == MODEL and result.usage.model_name == MODEL
    assert len(requests) == 1
    assert requests[0]["model"] == MODEL
    assert requests[0]["stream"] is stream and requests[0]["enable_thinking"] is False
    assert requests[0]["max_tokens"] == budget
    for other in {"chat_qwen_model", "chat_quick_model", "chat_detail_model", "screenshot_vision_model"} - {field}:
        assert getattr(config, other).startswith("synthetic-original-")


@pytest.mark.parametrize("field", ["chat_quick_model", "chat_detail_model"])
@pytest.mark.parametrize("empty", [None, "", "   "])
def test_candidate_shared_model_keeps_optional_stage_fallback(field, empty):
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "合成完整回答。"}}]})
    config = settings(chat_qwen_model=MODEL, **{field: empty})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        gateway = QwenCompatibleGateway(config, http_client=client)
        stage = "quick" if field == "chat_quick_model" else "detail"
        gateway._post_completion(prompt=prompt("interview-chat-" + stage), stream=False)
    assert requests[0]["model"] == MODEL
    assert config.screenshot_vision_model == "synthetic-original-vision"


def screenshot(ordinal: int, delivery: str) -> PreparedScreenshotImage:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (ordinal * 40, 100, 200)).save(buffer, format="JPEG", progressive=True)
    payload = buffer.getvalue()
    return PreparedScreenshotImage(
        image_id=f"synthetic-image-{ordinal}", session_id="synthetic-session", owner_user_id="synthetic-owner",
        filename=f"synthetic-page-{ordinal}.jpg", content_type="image/jpeg", object_key=f"private-synthetic-object-{ordinal}",
        size_bytes=len(payload), ordinal=ordinal, content_sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload), payload_bytes=payload,
        public_url=f"https://images.synthetic.invalid/page-{ordinal}.jpg" if delivery == "url" else None,
    )


@pytest.mark.parametrize("count", [1, 4])
@pytest.mark.parametrize("delivery", ["inline", "url"])
@pytest.mark.parametrize("stream", [False, True])
def test_candidate_vision_preserves_single_or_four_image_order(count, delivery, stream, monkeypatch):
    requests = []
    answer = "简要回答\n使用拓扑排序。\n\n---\n\n详细回答\n合并四页约束，支持负边权。"
    images = [screenshot(index, delivery) for index in range(1, count + 1)]
    def handle(request):
        requests.append(json.loads(request.content))
        assert str(request.url) == "https://vision.synthetic.invalid/v1/chat/completions"
        if stream:
            return httpx.Response(200, content=sse(answer), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"choices": [{"message": {"content": answer}}]})
    client_type = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client_type(transport=httpx.MockTransport(handle), **kwargs))
    config = settings(screenshot_vision_model=MODEL)
    gateway = OpenAICompatibleVisionGateway(config)
    if stream:
        text = "".join(gateway.stream_analyze(session_id="synthetic-session", instruction="按截图顺序合并解题", images=images, attempt=0))
        result = gateway.summary_from_stream(text=text, images=images)
    else:
        result = gateway.analyze(session_id="synthetic-session", instruction="按截图顺序合并解题", images=images, attempt=0)
    assert result.final_answer == answer and result.model_name == MODEL and result.image_count == count
    assert len(requests) == 1 and config.screenshot_max_images_per_task == 4
    sent = requests[0]
    assert sent["model"] == MODEL and sent["stream"] is stream and sent["enable_thinking"] is False
    content = sent["messages"][1]["content"]
    assert content[0]["type"] == "text" and len(content) == count + 1
    for actual, expected in zip(content[1:], images, strict=True):
        assert actual["type"] == "image_url"
        url = actual["image_url"]["url"]
        if delivery == "url":
            assert url == expected.public_url
        else:
            assert url.startswith("data:image/jpeg;base64,")
            assert base64.b64decode(url.split(",", 1)[1]) == expected.payload_bytes
    assert "private-synthetic-object" not in json.dumps(sent)
    assert config.chat_qwen_model == "synthetic-original-shared"


@pytest.mark.parametrize("case", RESUME_CASES, ids=[case["id"] for case in RESUME_CASES])
def test_candidate_resume_keeps_cn_json_schema_and_fact_guards(case):
    requests = []
    content = json.dumps(case["output"], ensure_ascii=False)
    transport = case.get("transport", "json")
    if transport == "fence":
        content = "```json\n" + content + "\n```"
    elif transport == "bom":
        content = "\ufeff" + content
    elif transport == "prose":
        content = "这是优化结果：\n" + content
    elif transport == "multiple_objects":
        content += "\n{}"

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": case.get("finish_reason", "stop"), "message": {"content": content}}]})

    provider = CNResumeOptimizerProvider(settings(chat_qwen_model=MODEL), transport=httpx.MockTransport(handle))
    async def generate():
        return await provider.generate(resume=case["resume"], jd=case["jd"], target_role="合成后端开发")
    if case["expectedAccepted"]:
        review, draft = asyncio.run(generate())
        assert 0 <= review["overallScore"] <= 100 and review["roleMatchingAssessed"] is bool(case["jd"])
        assert case["expectedDraft"] == draft
        assert review["editSummary"]["appliedCount"] >= 1
    else:
        with pytest.raises(ResumeProviderError) as exc:
            asyncio.run(generate())
        assert exc.value.category == "invalid_output"
    assert len(requests) == 1  # No blind generation retry or JSON repair call.
    assert requests[0]["model"] == MODEL and requests[0]["stream"] is False
    assert requests[0]["enable_thinking"] is False and requests[0]["max_tokens"] == 6500
    assert json.loads(requests[0]["messages"][1]["content"])["resume"] == case["resume"]


def test_candidate_evals_are_synthetic_and_cover_required_capabilities():
    assert len({case["id"] for case in EVALS}) == len(EVALS)
    assert all(case["synthetic"] is True and case["model"] == MODEL for case in EVALS)
    assert {"quick", "detail", "vision", "resume", "summary", "question", "report", "web_search"} <= {case["operation"] for case in EVALS}
    vision = [case for case in EVALS if case["operation"] == "vision"]
    assert {len(case["images"]) for case in vision} == {1, 4}
    assert any(case["expectedAccepted"] for case in RESUME_CASES)
    assert any(not case["expectedAccepted"] for case in RESUME_CASES)
