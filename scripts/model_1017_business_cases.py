"""Bounded synthetic business probes through existing regional adapters.

This module has no CLI and prints nothing. A reviewed caller supplies candidate
Settings and consumes the returned safe metadata. It never imports app.deps,
creates a service lifecycle, accesses a repository or retries a provider call.
The same source can be exec'd inside either region's pinned image.
"""
from __future__ import annotations

import asyncio
from collections import Counter
import logging
import re
from time import monotonic
from types import SimpleNamespace


TARGET_MODEL = "deepseek-v4.1-flash-1017"
CN_RESUME = (
    "# 合成候选人\nsynthetic@example.invalid\n"
    "负责使用Python开发数据接口，为12个团队提供服务。\n"
    "2024年 合成科技有限公司\n教育：合成大学 本科。"
)
CN_JD = "合成后端岗位要求Python数据接口开发经验，熟悉PostgreSQL；容器编排经验为加分项。"
GLOBAL_RESUME = (
    "# Synthetic Candidate\nsynthetic@example.invalid\n"
    "## Experience\nSynthetic Example Company | 2024\n"
    "Worked on Python data interfaces and tested PostgreSQL queries for 12 internal teams.\n"
    "Helped with Python interface tests and documented test results.\n"
    "## Education\nSynthetic Example University, Bachelor degree."
)
GLOBAL_JD = "Synthetic backend role: Python data interfaces and PostgreSQL queries. Container orchestration is a desired skill."
MOCK_RESUME = "合成候选人参与Python订单接口开发，使用PostgreSQL唯一键约束重复业务编号，没有核实的吞吐或延迟改进数字。"
MOCK_QUESTION = "如何避免相同业务编号重复创建订单？"
MOCK_ANSWER = "我先使用PostgreSQL唯一键约束重复业务编号，并在同一事务中检查和写入订单；还没有实际吞吐或延迟改进数据。"

_ERROR_CATEGORIES = {
    "invalid_output", "provider_timeout", "provider_unavailable", "provider_unconfigured",
    "interrupted", "source_unavailable",
}
_DIAGNOSTIC_REASONS = {
    "provider_timeout", "provider_http_error", "provider_unconfigured", "response_too_large",
    "response_encoding_invalid", "provider_envelope_invalid", "provider_finish_length", "provider_finish_invalid",
    "content_encoding_invalid", "content_json_invalid", "content_json_ambiguous", "review_schema_invalid",
    "dimension_set_invalid", "evidence_quote_missing", "role_evidence_missing", "explanation_language_invalid",
    "missing_facts_language_invalid", "edit_quote_not_unique", "fact_numbers_changed", "fact_contact_changed",
    "fact_english_content_added", "fact_english_content_removed", "fact_credentials_changed",
    "fact_dates_counts_changed", "fact_negation_changed", "fact_entities_changed", "fact_responsibility_changed",
    "fact_skills_changed", "edit_spans_overlap", "draft_invalid", "no_effective_edits",
    "slot_wait_timeout", "provider_transport_error", "context_limit", "response_json_invalid",
    "incomplete_response", "response_envelope_invalid", "structured_output_invalid", "question_schema_invalid",
    "report_schema_invalid", "report_evidence_invalid", "repeated_question", "internal_error",
}


def _safe_failure(error):
    """Return only enumerated labels, never str(error), URLs or model content."""
    category = getattr(error, "category", None)
    error_type = category if type(category) is str and category in _ERROR_CATEGORIES else "adapter_error"
    if isinstance(error, (ImportError, ModuleNotFoundError)):
        error_type = "adapter_unavailable"
    elif isinstance(error, TimeoutError):
        error_type = "provider_timeout"
    elif type(error).__name__ == "MockGenerationUnavailable":
        error_type = "mock_generation_unavailable"
    diagnostic = getattr(error, "diagnostic", None)
    reason = diagnostic.get("reason") if type(diagnostic) is dict else getattr(error, "error_category", None)
    safe_reason = reason if type(reason) is str and reason in _DIAGNOSTIC_REASONS else "unclassified_adapter_failure"
    return error_type, safe_reason


def _result(operation, started, checks, error=None):
    checks = {key: bool(value) for key, value in checks.items()}
    passed = bool(checks) and all(checks.values()) and error is None
    error_type, reason = (None, None) if passed else (
        _safe_failure(error) if error is not None else ("validation_failed", "synthetic_checks_failed")
    )
    return {
        "operation": operation, "model": TARGET_MODEL, "syntheticOnly": True,
        "passed": passed, "errorType": error_type, "diagnosticReason": reason,
        "seconds": round(monotonic() - started, 3), "checks": checks,
    }


def _resume_checks(review, draft, *, resume, jd, is_cn):
    expected_dimensions = {"completeness", "impact", "clarity", "structure"} | ({"roleMatch"} if jd else set())
    dimensions = review.get("dimensions", [])
    evidence = [item for section in (dimensions, review.get("suggestions", [])) for entry in section for item in entry.get("evidence", [])]
    checks = {
        "providerAndExistingValidatorsCompleted": True,
        "expectedDimensions": len(dimensions) == len(expected_dimensions) and {item.get("key") for item in dimensions} == expected_dimensions,
        "scoreIsBoundedInteger": type(review.get("overallScore")) is int and 0 <= review["overallScore"] <= 100,
        "roleMatchAssessed": review.get("roleMatchingAssessed") is bool(jd),
        "literalSourceEvidence": bool(evidence) and all(item.get("quote", "") and item["quote"] in (resume if item.get("source") == "resume" else jd) for item in evidence),
        "contactPreserved": "synthetic@example.invalid" in draft,
        "sourceNumbersPreserved": Counter(re.findall(r"\d+", draft)) == Counter(re.findall(r"\d+", resume)),
        "sourceSkillsPreserved": "Python" in draft and (is_cn or "PostgreSQL" in draft),
        "jdSkillNotInserted": "Kubernetes" not in draft and "容器编排" not in draft and "orchestration" not in draft,
    }
    # CN current behavior requires substantive safe edits. Global's approved
    # original contract accepts edits=[]; report that fact without strengthening
    # or weakening its existing acceptance rules here.
    if is_cn:
        summary = review.get("editSummary", {})
        canonical = lambda text: "".join(char for char in text.casefold() if char.isalnum())
        checks["safeSubstantiveEditApplied"] = type(summary.get("appliedCount")) is int and summary["appliedCount"] >= 1 and canonical(draft) != canonical(resume)
    return checks


async def _resume_case(settings, region, *, with_jd=True):
    started = monotonic()
    operation = "resume_" + region + ("" if with_jd else "_no_jd")
    checks = {"providerAndExistingValidatorsCompleted": False}
    try:
        if region == "cn":
            from app.services.cn_resume_optimizer_provider import CNResumeOptimizerProvider
            provider, resume, jd, role = CNResumeOptimizerProvider(settings), CN_RESUME, CN_JD, "合成后端开发"
        else:
            from app.services.resume_optimizer_provider import ResumeOptimizerProvider
            provider, resume, jd, role = ResumeOptimizerProvider(settings), GLOBAL_RESUME, GLOBAL_JD, "Synthetic backend developer"
        if not with_jd:
            jd = ""
        review, draft = await provider.generate(resume=resume, jd=jd, target_role=role)
        checks = _resume_checks(review, draft, resume=resume, jd=jd, is_cn=region == "cn")
        return _result(operation, started, checks)
    except Exception as error:
        return _result(operation, started, checks, error)


async def _mock_case(settings, operation):
    started = monotonic()
    checks = {"providerAndExistingValidatorsCompleted": False}
    try:
        from app.services.mock_interview_generation import MockInterviewGenerator
        from app.services.mock_interview_rounds import MockRound
        generator = MockInterviewGenerator(settings)
        if operation == "mock_question_cn":
            question = await generator.question(resume=MOCK_RESUME, target_role="合成后端开发", rounds=())
            checks = {
                "providerAndExistingValidatorsCompleted": True,
                "singleQuestion": question.question.count("？") + question.question.count("?") == 1,
                "questionAndFocusNonempty": bool(question.question.strip()) and bool(question.focus.strip()),
                "groundedInSyntheticSkills": any(term in question.question for term in ("Python", "PostgreSQL", "订单", "唯一", "重复", "幂等")),
                "contactNotRepeated": "synthetic@example.invalid" not in question.question,
            }
        else:
            report = await generator.report(resume=MOCK_RESUME, target_role="合成后端开发",
                rounds=(MockRound("synthetic-q1", MOCK_QUESTION, MOCK_ANSWER),))
            checks = {
                "providerAndExistingValidatorsCompleted": True,
                "scoreIsBoundedInteger": type(report.overall_score) is int and 0 <= report.overall_score <= 100,
                "oneConfirmedAnswerFeedback": len(report.feedback) == 1 and report.feedback[0].question_id == "synthetic-q1",
                "literalAnswerQuote": len(report.feedback) == 1 and bool(report.feedback[0].answer_quote.strip()) and report.feedback[0].answer_quote in MOCK_ANSWER,
                "serverAnswerStructureUsed": len(report.feedback) == 1 and report.feedback[0].answer_quote in report.feedback[0].suggestion,
                "partialReportDisclosed": report.summary.startswith("部分报告（已回答 1/10 题）。"),
            }
        return _result(operation, started, checks)
    except Exception as error:
        return _result(operation, started, checks, error)


async def _summary_case(settings, kind):
    started = monotonic()
    checks = {"remoteSummaryReturned": False}
    try:
        from importlib import import_module
        summary_module = import_module("app.services.document_processing")
        DocumentProcessingService = summary_module.DocumentProcessingService
        service = object.__new__(DocumentProcessingService)
        service.settings = settings
        service.logger = logging.Logger("synthetic-model-1017-summary", level=logging.CRITICAL + 1)
        service.logger.disabled = True
        service.logger.propagate = False
        # Both deployed summary adapters use a Chinese factual-compression
        # contract, including Global's older material-worker implementation.
        source = (
            "合成候选人在2024年参与Python数据接口开发，使用PostgreSQL唯一键防止重复业务编号，为12个内部团队提供服务。"
            if kind == "resume" else
            "合成后端岗位要求Python数据接口开发经验，熟悉PostgreSQL唯一键和事务；没有额外学历或年限要求。"
        )
        document = SimpleNamespace(document_kind=kind, document_id="synthetic-model-1017-" + kind)
        observed = {"requests": 0, "responses": 0, "candidateRequest": False, "http200": False, "finishStop": False}
        original_httpx = summary_module.httpx

        def observe_request(request):
            import json
            observed["requests"] += 1
            try:
                payload = json.loads(request.content)
                observed["candidateRequest"] = payload.get("model") == TARGET_MODEL and payload.get("enable_thinking") is False and payload.get("stream") is False
            except Exception:
                observed["candidateRequest"] = False

        def observe_response(response):
            observed["responses"] += 1
            observed["http200"] = response.status_code == 200
            try:
                response.read()
                payload = response.json()
                observed["finishStop"] = payload["choices"][0].get("finish_reason") == "stop"
            except Exception:
                observed["finishStop"] = False

        class LocalSummaryHttpx:
            def __getattr__(self, name):
                return getattr(original_httpx, name)

            def Client(self, **kwargs):
                hooks = {key: list(value) for key, value in kwargs.pop("event_hooks", {}).items()}
                hooks.setdefault("request", []).append(observe_request)
                hooks.setdefault("response", []).append(observe_response)
                return original_httpx.Client(**kwargs, event_hooks=hooks)

        # Replace only this imported module's binding in the independent probe
        # process. Shared httpx and other providers are never monkeypatched.
        summary_module.httpx = LocalSummaryHttpx()
        try:
            summary = await asyncio.to_thread(service._try_remote_interview_summary, document=document, clean_text=source)
        finally:
            summary_module.httpx = original_httpx
        text = summary if type(summary) is str else ""
        body = re.sub(r"(?m)^\s*\d+[.)、]\s*", "", text)
        prefix = "简历面试摘要：\n" if kind == "resume" else "职位 JD面试摘要：\n"
        checks = {
            "remoteSummaryReturned": bool(text.strip()),
            "summaryCandidateNonThinkingRequest": observed["requests"] == 1 and observed["candidateRequest"],
            "summaryProviderComplete": observed["responses"] == 1 and observed["http200"] and observed["finishStop"],
            "existingPrefixAndLimit": text.startswith(prefix) and 0 < len(text.removeprefix(prefix)) <= 900,
            "sourceSkillsRetained": "Python" in text and "PostgreSQL" in text,
            "noInventedNumbers": set(re.findall(r"\d+", body)) <= set(re.findall(r"\d+", source)),
        }
        return _result("summary_" + kind, started, checks)
    except Exception as error:
        return _result("summary_" + kind, started, checks, error)


async def run_business_cases(settings, *, worker_only=False):
    """Return at most 6 CN / 4 Global / 2 worker safe results, sequentially.

    The caller must supply a Settings copy selecting TARGET_MODEL. No feature
    flag is changed: Global mock remains untested because it is disabled there.
    All requests use existing adapters and their original time/token budgets.
    """
    started = monotonic()
    if getattr(settings, "chat_qwen_model", None) != TARGET_MODEL:
        return [_result("business_configuration", started, {"candidateModelConfigured": False})]
    region = getattr(settings, "product_edition", None)
    if not worker_only and region not in {"cn", "global"}:
        return [_result("business_configuration", started, {"knownBackendRegion": False})]
    results = []
    if not worker_only:
        results.append(await _resume_case(settings, region))
        results.append(await _resume_case(settings, region, with_jd=False))
        if region == "cn":
            results.append(await _mock_case(settings, "mock_question_cn"))
            results.append(await _mock_case(settings, "mock_report_cn"))
    results.append(await _summary_case(settings, "resume"))
    results.append(await _summary_case(settings, "job_description"))
    return results
