"""Offline Global contracts for the proposed 1017 provider configuration.

Every request uses MockTransport and synthetic content. These checks validate
our wire contract and rejection rules, not the model's live permission, quality,
latency, or multimodal support.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.core.config import REPO_ROOT, Settings
from app.core.errors import DomainRequestError
from app.modules import mock_interview as mock_api
from app.ports.chat import PromptBuildResult
from app.services.chat_service import ChatService, FilePromptTemplateAdapter, QwenCompatibleGateway
from app.services import document_processing
from app.services.document_processing import DocumentProcessingService
from app.services.resume_optimizer_provider import ResumeOptimizerProvider, ResumeProviderError


MODEL = "deepseek-v4.1-flash-1017"
RESUME = "SYNTHETIC CANDIDATE\nBuilt Python cache with 20 tests in 2024."
GLOBAL_EVALS = [json.loads(line) for line in (
    REPO_ROOT / "ai/evals/global-model-v41-flash-1017.jsonl").read_text(encoding="utf-8").splitlines()]


def settings(**updates) -> Settings:
    return Settings(_env_file=None, product_edition="global", chat_qwen_model=MODEL,
        chat_quick_model=MODEL, chat_detail_model=MODEL,
        chat_qwen_base_url="https://synthetic.invalid/v1", chat_qwen_api_key="synthetic",
        **updates)


def review() -> dict:
    evidence = [{"source": "resume", "quote": "Built Python cache"}]
    return {
        "dimensions": [{"key": key, "score": 80,
            "reason": "The synthetic resume describes a supported project.",
            "evidence": deepcopy(evidence)}
            for key in ("completeness", "impact", "clarity", "structure")],
        "suggestions": [{"priority": "medium", "title": "Clarify testing evidence",
            "explanation": "The source lists tests but does not describe the test process.",
            "recommendation": "Add verifiable testing details if available.",
            "evidence": deepcopy(evidence)}],
        "missingFacts": ["Describe verifiable testing details if available."], "edits": [],
    }


@pytest.mark.parametrize("stage", ["quick", "detail", "continuation"])
@pytest.mark.parametrize("stream", [False, True])
def test_global_1017_chat_keeps_english_prompt_and_non_thinking_contract(monkeypatch, stage, stream):
    # The remote branch is exercised only through the supplied fake transport.
    monkeypatch.setenv("OFFERSTEADY_TEST_USE_REMOTE_CHAT", "1")
    cfg = settings()
    system, config = FilePromptTemplateAdapter(cfg).load_stage_prompt(stage, "en-US")
    prompt = PromptBuildResult(system_prompt=system, user_prompt="Describe a bounded cache.",
        rendered_prompt=system, prompt_config=config, retrieval_excerpt_count=0)
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        if stream:
            events = [
                {"choices": [{"delta": {"reasoning_content": "HIDDEN SYNTHETIC REASONING"}}]},
                {"choices": [{"delta": {"content": "Use a bounded cache."}, "finish_reason": "stop"}]},
            ]
            return httpx.Response(200, text="".join("data: " + json.dumps(e) + "\n\n" for e in events))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Use a bounded cache."},
            "finish_reason": "stop"}]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        gateway = QwenCompatibleGateway(cfg, http_client=client)
        if stream:
            chunks = list(gateway.stream_generate(question="Describe a bounded cache.", prompt=prompt, attempt=0))
            assert "".join(chunk.text for chunk in chunks) == "Use a bounded cache."
            assert chunks[-1].is_final
        else:
            result = gateway.generate(question="Describe a bounded cache.", prompt=prompt, stream=False, attempt=0)
            assert result.final_text == "Use a bounded cache."
            assert result.model_name == MODEL
    assert len(requests) == 1
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False
    assert requests[0]["stream"] is stream
    assert "English" in requests[0]["messages"][0]["content"]
    assert requests[0]["max_tokens"] <= 1400


def test_global_1017_configuration_does_not_enable_closed_features(monkeypatch):
    cfg = settings(global_resume_optimizer_enabled=True)
    monkeypatch.setattr(mock_api, "get_settings", lambda: cfg)
    assert cfg.global_resume_optimizer_enabled is True
    assert cfg.global_mock_interview_enabled is False
    assert cfg.global_web_answer_enabled is False
    assert cfg.web_search_enabled is False
    with pytest.raises(DomainRequestError) as blocked:
        mock_api.require_mock_runtime()
    assert blocked.value.error_code == "mock_not_enabled"
    with pytest.raises(DomainRequestError) as blocked:
        ChatService._ensure_web_search_allowed(SimpleNamespace(settings=cfg), enabled=True)
    assert blocked.value.error_code == "web_search_not_available"


def test_global_1017_resume_keeps_strict_json_english_and_factual_validation():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
            "message": {"content": json.dumps(review())}}]})

    provider = ResumeOptimizerProvider(settings(), transport=httpx.MockTransport(handle))
    result, draft = asyncio.run(provider.generate(resume=RESUME, jd="", target_role="Backend engineer"))
    assert result["overallScore"] == 80
    assert result["roleMatchingAssessed"] is False
    assert draft == RESUME
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False
    assert requests[0]["stream"] is False
    assert requests[0]["max_tokens"] == 6500
    assert "English" in requests[0]["messages"][0]["content"]
    assert "response_format" not in requests[0], "Do not require unsupported JSON Schema from the provider"


@pytest.mark.parametrize("invalid", ["extra_field", "string_score", "unsupported_quote", "wrong_language",
    "invented_metric", "fenced_json", "incomplete_response", "oversized_response"])
def test_global_1017_does_not_relax_resume_rejection_rules(invalid):
    payload = review()
    if invalid == "extra_field":
        payload["unexpected"] = "Do not ignore schema drift."
    elif invalid == "string_score":
        payload["dimensions"][0]["score"] = "80"
    elif invalid == "unsupported_quote":
        payload["dimensions"][0]["evidence"][0]["quote"] = "Unsupported synthetic source."
    elif invalid == "wrong_language":
        payload["dimensions"][0]["reason"] = "这不是规定的英文评估结果。"
    elif invalid == "invented_metric":
        payload["edits"] = [{"sourceQuote": "Built Python cache with 20 tests in 2024.",
            "replacement": "Built Python cache with 20 tests in 2024 and improved latency by 90%."}]
    content = json.dumps(payload)
    if invalid == "fenced_json":
        content = "```json\n" + content + "\n```"
    elif invalid == "oversized_response":
        content = "x" * (256 * 1024)

    def handle(_request):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "length" if invalid == "incomplete_response" else "stop",
            "message": {"content": content}}]})

    provider = ResumeOptimizerProvider(settings(), transport=httpx.MockTransport(handle))
    with pytest.raises(ResumeProviderError) as rejected:
        asyncio.run(provider.generate(resume=RESUME, jd="", target_role="Backend engineer"))
    assert rejected.value.category == "invalid_output"


@pytest.mark.parametrize("document_kind", ["resume", "job_description"])
@pytest.mark.parametrize("outcome", ["success", "timeout", "provider_error", "empty"])
def test_global_1017_worker_summary_is_non_thinking_with_existing_budget_and_fallback(
        monkeypatch, document_kind, outcome):
    requests, budgets = [], []
    original_client = httpx.Client
    source = "SYNTHETIC: Built a Python cache with PostgreSQL. No performance measurements are available."
    generated = "Synthetic candidate used Python and PostgreSQL; no performance measurements are available."

    def handle(request):
        requests.append(json.loads(request.content))
        if outcome == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if outcome == "provider_error":
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {
            "content": generated if outcome == "success" else ""}}]})

    def client(*args, **kwargs):
        budgets.append(kwargs["timeout"])
        return original_client(*args, transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(document_processing.httpx, "Client", client)
    service = DocumentProcessingService(settings=settings(), logger=logging.getLogger("synthetic-summary"),
        document_repository=Mock(), task_repository=Mock(), parser_service=Mock(), embedding_pipeline=Mock())
    document = SimpleNamespace(document_id="synthetic-summary", document_kind=document_kind)
    result = service._build_interview_summary(document=document, markdown=source)
    assert len(requests) == 1
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False
    assert requests[0]["stream"] is False
    assert requests[0]["temperature"] == 0.1
    assert budgets[0].connect == 2.0
    assert budgets[0].read == 8.0
    assert budgets[0].write == 4.0
    assert budgets[0].pool == 2.0
    if outcome == "success":
        assert result.endswith(generated)
    else:
        assert result == service._extractive_interview_summary(document=document, clean_text=source)


@pytest.mark.parametrize("case", [row for row in GLOBAL_EVALS if row["operation"] == "resume"],
    ids=lambda row: row["id"])
def test_global_1017_resume_eval_uses_unmodified_regional_validator(case):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        content = json.dumps(case["output"])
        if case.get("wire_format") == "fenced_json":
            content = "```json\n" + content + "\n```"
        return httpx.Response(200, json={"choices": [{"finish_reason": case.get("finish_reason", "stop"),
            "message": {"content": content}}]})

    provider = ResumeOptimizerProvider(settings(), transport=httpx.MockTransport(handle))
    if case["expectedAccepted"]:
        result, draft = asyncio.run(provider.generate(resume=case["resume"], jd=case["jd"],
            target_role="Synthetic backend engineer"))
        assert draft == case["expectedDraft"]
        assert result["roleMatchingAssessed"] is bool(case["jd"])
    else:
        with pytest.raises(ResumeProviderError) as rejected:
            asyncio.run(provider.generate(resume=case["resume"], jd=case["jd"],
                target_role="Synthetic backend engineer"))
        assert rejected.value.category == "invalid_output"
    assert len(requests) == 1
    assert requests[0]["model"] == MODEL
    assert requests[0]["enable_thinking"] is False
