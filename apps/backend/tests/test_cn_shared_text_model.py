import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import REPO_ROOT, Settings
from app.services.document_processing import DocumentProcessingService
from app.services.mock_interview_generation import MockInterviewGenerator
from app.services.mock_interview_rounds import MockRound


MODEL = "deepseek-v4.1-flash"


def cn_settings():
    return Settings(
        _env_file=None, environment="test", product_edition="cn",
        chat_qwen_model=MODEL, chat_quick_model="independent-quick",
        chat_detail_model="independent-detail", chat_qwen_api_key="synthetic-key",
        chat_qwen_base_url="https://synthetic.invalid/v1",
    )


@pytest.mark.parametrize("kind,label", [("resume", "简历"), ("job_description", "职位 JD")])
def test_summary_uses_shared_v4_1_non_thinking_and_keeps_output(kind, label, monkeypatch):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "- 合成订单项目，使用 PostgreSQL 唯一键实现幂等。"}}]})

    client_type = httpx.Client
    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    service = object.__new__(DocumentProcessingService)
    service.settings = cn_settings()
    service.logger = logging.getLogger("test-cn-summary")
    document = SimpleNamespace(document_kind=kind, document_id="synthetic-document")
    summary = service._try_remote_interview_summary(document=document, clean_text="合成订单项目，使用 PostgreSQL。")
    assert summary.startswith(label + "面试摘要：\n")
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False
    assert requests[0]["stream"] is False
    assert requests[0]["temperature"] == 0.1
    assert service.settings.chat_quick_model == "independent-quick"
    assert service.settings.chat_detail_model == "independent-detail"


def test_summary_provider_failure_keeps_existing_extractive_fallback(monkeypatch):
    client_type = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "synthetic-unavailable"}))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    service = object.__new__(DocumentProcessingService)
    service.settings = cn_settings()
    service.logger = logging.getLogger("test-cn-summary")
    document = SimpleNamespace(document_kind="resume", document_id="synthetic-document")
    summary = service._build_interview_summary(document=document, markdown="合成项目：负责订单服务，使用 PostgreSQL 唯一键。")
    assert summary.startswith("简历面试摘要：")
    assert "PostgreSQL" in summary


@pytest.mark.parametrize("operation", ["question", "report"])
def test_mock_operations_use_shared_model_not_stage_overrides(operation):
    requests = []
    payload = {"question": "你如何保证订单幂等？", "focus": "幂等设计"} if operation == "question" else {
        "summary": "部分练习已展示基本幂等设计思路。",
        "dimensions": {"relevance": 80, "clarity": 70, "depth": 60, "evidence": 50},
        "feedback": [{"question_id": "q1", "answer_quote": "设置唯一键", "strength": "有明确方案",
                      "improvement": "还需验证并发", "suggestion": "模型建议不会直接作为经历使用。"}],
        "practice_priorities": ["验证并发重复请求"],
    }

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload)}}]})

    service = MockInterviewGenerator(cn_settings(), transport=httpx.MockTransport(handle))
    if operation == "question":
        result = asyncio.run(service.question(resume="合成订单项目", target_role="后端", rounds=()))
        assert result.question.endswith("？")
    else:
        result = asyncio.run(service.report(resume="合成订单项目", target_role="后端",
                                           rounds=(MockRound("q1", "如何幂等？", "我先设置唯一键。"),)))
        assert result.overall_score == 65 and "1/10" in result.summary
        assert result.feedback[0].answer_quote == "设置唯一键"
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False


def test_shared_model_config_example_and_eval_fixture_are_current():
    example = dict(line.split("=", 1) for line in (REPO_ROOT / ".env.example").read_text().splitlines()
                   if line.startswith("OFFERSTEADY_CHAT_") and "=" in line)
    assert example["OFFERSTEADY_CHAT_QWEN_MODEL"] == MODEL
    fixtures = [json.loads(line) for line in (REPO_ROOT / "ai/evals/cn-shared-text-model-v4-1-flash.jsonl").read_text().splitlines()]
    assert len({row["id"] for row in fixtures}) == 4
    assert all(row["model"] == MODEL for row in fixtures)
    assert {row["operation"] for row in fixtures} == {"summary", "question", "report"}
