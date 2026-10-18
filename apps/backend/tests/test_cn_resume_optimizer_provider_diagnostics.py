"""Synthetic-only fixed diagnostics and strict, whole-output JSON wrappers."""
import asyncio
from copy import deepcopy
import json

import httpx
import pytest

from app.core.config import REPO_ROOT, Settings
from app.services.cn_resume_optimizer_diagnostics import (
    error_message_for_diagnostic, failure_diagnostic, normalize_failure_diagnostic,
)
from app.services.cn_resume_optimizer_provider import (
    CNResumeOptimizerProvider, ResumeProviderError, _parse_provider_content,
    validate_resume_review,
)
from cn_resume_optimizer_test_support import JD, QUOTE, RESUME, review_payload


PRIVATE = "SYNTHETIC_PRIVATE_DIAGNOSTIC_SENTINEL"


def generate_response(*, content=None, body=None, finish="stop", status=200):
    requests = []
    async def respond(request):
        requests.append(request)
        if isinstance(body, Exception):
            raise body
        if body is not None:
            return httpx.Response(status, content=body)
        return httpx.Response(status, json={"choices": [{"finish_reason": finish,
            "message": {"content": content}}]})
    settings = Settings(_env_file=None).model_copy(update={"product_edition": "cn",
        "chat_qwen_api_key": PRIVATE, "chat_qwen_base_url": "https://provider.invalid/v1"})
    provider = CNResumeOptimizerProvider(settings, transport=httpx.MockTransport(respond))
    return provider, requests


def assert_failure(call, reason, *, category="invalid_output"):
    with pytest.raises(ResumeProviderError) as caught:
        call()
    error = caught.value
    assert error.category == str(error) == category
    assert error.diagnostic == failure_diagnostic(reason)
    assert error.diagnostic is not None
    assert PRIVATE not in str(error) + repr(error) + json.dumps(error.__dict__)
    assert PRIVATE not in error_message_for_diagnostic(error.diagnostic)


@pytest.mark.parametrize("reason", [
    "evidence_quote_missing", "fact_numbers_changed", "provider_timeout",
    "runtime_timeout", "runtime_interrupted", "runtime_internal_error",
    "runtime_repository_unavailable",
])
def test_diagnostic_pair_is_fixed_and_fresh(reason):
    first = failure_diagnostic(reason)
    assert normalize_failure_diagnostic(first) == first
    assert error_message_for_diagnostic(first)
    first["reason"] = PRIVATE
    assert failure_diagnostic(reason)["reason"] == reason
    assert normalize_failure_diagnostic(first) is None


@pytest.mark.parametrize("value", [None, "provider_timeout", [], 1,
    {"stage": "facts", "reason": PRIVATE},
    {"stage": PRIVATE, "reason": "fact_numbers_changed"},
    {"stage": "schema", "reason": "fact_numbers_changed"},
    {"stage": "facts", "reason": "fact_numbers_changed", "raw": PRIVATE},
    {"stage": "facts", "reason": [PRIVATE]},
    {"reason": "fact_numbers_changed"},
])
def test_unknown_or_unsafe_diagnostic_has_no_message(value):
    assert normalize_failure_diagnostic(value) is None
    assert error_message_for_diagnostic(value) is None


def test_unknown_exception_labels_remain_generic_and_never_echo_values():
    error = ResumeProviderError(PRIVATE, reason=PRIVATE)
    assert str(error) == "invalid_output"
    assert error.diagnostic is None
    assert PRIVATE not in repr(error) + json.dumps(error.__dict__)
    assert ResumeProviderError({"raw": PRIVATE}, reason=[]).category == "invalid_output"


@pytest.mark.parametrize("wrapper", [
    lambda text: text,
    lambda text: " \n\t" + text + "\n ",
    lambda text: "\ufeff \n" + text + "\t",
    lambda text: "```json\n" + text + "\n```",
    lambda text: " \ufeff \n```json\r\n" + text + "\r\n``` \t",
])
def test_whole_valid_output_wrappers_pass_without_changing_result(wrapper):
    raw = review_payload()
    raw["missingFacts"] = ["请保留说明内的空白和符号：  示例  。"]
    content = json.dumps(raw, ensure_ascii=False)
    provider, requests = generate_response(content=wrapper(content))
    expected = validate_resume_review(raw, resume=RESUME, jd="")
    actual = asyncio.run(provider.generate(resume=RESUME, jd="", target_role=""))
    assert actual == expected
    assert actual[0]["missingFacts"] == raw["missingFacts"]
    assert len(requests) == 1


@pytest.mark.parametrize("content", [
    lambda text: "说明：" + text,
    lambda text: text + "\n结果如上。",
    lambda text: text + text,
    lambda text: "```json\n" + text + "\n```\n```json\n" + text + "\n```",
    lambda text: "```JSON\n" + text + "\n```",
    lambda text: "```\n" + text + "\n```",
    lambda text: "```json\n" + text,
    lambda text: "\ufeff\ufeff" + text,
    lambda text: text[:-1],
    lambda text: "[]",
    lambda text: "null",
    lambda text: "true",
    lambda text: "42",
    lambda text: json.dumps(text),
    lambda text: '{"private":NaN}',
    lambda text: '{"private":Infinity}',
    lambda text: '{"private":-Infinity}',
    lambda text: '{"private":1e9999}',
])
def test_never_extracts_or_repairs_ambiguous_or_invalid_content(content):
    text = json.dumps(review_payload(), ensure_ascii=False)
    provider, requests = generate_response(content=content(text))
    assert_failure(lambda: asyncio.run(provider.generate(resume=RESUME, jd="", target_role="")), "content_json_invalid")
    assert len(requests) == 1


@pytest.mark.parametrize("content", [
    '{"private":"' + PRIVATE + '","private":"' + PRIVATE + '"}',
    '{"nested":{"same":1,"same":2}}',
])
def test_rejects_duplicate_keys_even_when_nested_without_exposing_key(content):
    assert_failure(lambda: _parse_provider_content(content), "content_json_ambiguous")


@pytest.mark.parametrize("body,reason", [
    (b"\xff", "response_encoding_invalid"),
    (b"x" * (256 * 1024 + 1), "response_too_large"),
    (b"[]", "provider_envelope_invalid"),
    (b'{"choices":[],"choices":[]}', "provider_envelope_invalid"),
    (b'{"private":NaN}', "provider_envelope_invalid"),
    (b'{"choices":[]}', "provider_envelope_invalid"),
    (b'{"choices":[null]}', "provider_envelope_invalid"),
    (b'{"choices":[{"finish_reason":"stop","message":{}}]}', "provider_envelope_invalid"),
])
def test_transport_and_envelope_failures_have_fixed_diagnostics(body, reason):
    provider, requests = generate_response(body=body)
    assert_failure(lambda: asyncio.run(provider.generate(resume=RESUME, jd="", target_role="")), reason)
    assert len(requests) == 1


@pytest.mark.parametrize("finish,reason", [("length", "provider_finish_length"),
    ("content_filter", "provider_finish_invalid"), (None, "provider_finish_invalid")])
def test_nonstop_is_rejected_even_with_otherwise_valid_content(finish, reason):
    provider, _ = generate_response(content=json.dumps(review_payload()), finish=finish)
    assert_failure(lambda: asyncio.run(provider.generate(resume=RESUME, jd="", target_role="")), reason)


def test_content_encoding_and_wrong_envelope_content_type_are_distinct():
    assert_failure(lambda: _parse_provider_content("\ud800" + PRIVATE), "content_encoding_invalid")
    assert_failure(lambda: _parse_provider_content({"raw": PRIVATE}), "provider_envelope_invalid")


@pytest.mark.parametrize("category,reason", [("provider_timeout", "provider_timeout"),
    ("provider_unavailable", "provider_http_error"), ("provider_unconfigured", "provider_unconfigured")])
def test_nonoutput_error_categories_are_preserved_without_raw_exception(category, reason):
    if category == "provider_timeout":
        provider, requests = generate_response(body=httpx.ReadTimeout(PRIVATE))
    else:
        provider, requests = generate_response(status=503, body=PRIVATE.encode())
    if category == "provider_unconfigured":
        provider.settings = provider.settings.model_copy(update={"chat_qwen_api_key": ""})
    assert_failure(lambda: asyncio.run(provider.generate(resume=RESUME, jd="", target_role="")), reason, category=category)
    assert len(requests) == (0 if category == "provider_unconfigured" else 1)


@pytest.mark.parametrize("quote,replacement,reason", [
    ("服务12个团队", "服务13个团队", "fact_numbers_changed"),
    ("synthetic@example.invalid", "changed@example.invalid", "fact_contact_changed"),
    (QUOTE, "使用Python和Kubernetes开发数据接口", "fact_english_content_added"),
    ("使用Python和Django开发接口", "使用Python开发接口", "fact_english_content_removed"),
    ("本科", "硕士", "fact_credentials_changed"),
    ("二〇二四年入职", "二〇二五年入职", "fact_dates_counts_changed"),
    ("未参与接口开发", "参与接口开发", "fact_negation_changed"),
    ("负责甲公司接口开发", "负责乙公司接口开发", "fact_entities_changed"),
    ("参与接口开发", "主导接口开发", "fact_responsibility_changed"),
    ("负责接口开发", "高级负责接口开发", "fact_responsibility_changed"),
    ("负责接口开发", "负责微服务接口开发", "fact_skills_changed"),
    ("assisted Python development", "developed Python development", "fact_responsibility_changed"),
    ("developed Python", "managed Python", "fact_responsibility_changed"),
])
def test_each_fact_guard_has_a_fixed_reason_and_still_rejects(quote, replacement, reason):
    raw = review_payload(edits=False)
    raw["edits"] = [{"sourceQuote": quote, "replacement": replacement}]
    source = RESUME if quote in RESUME else RESUME + "\n" + quote
    assert_failure(lambda: validate_resume_review(raw, resume=source, jd=""), reason)


@pytest.mark.parametrize("kind,reason", [
    ("schema", "review_schema_invalid"), ("dimensions", "dimension_set_invalid"),
    ("evidence", "evidence_quote_missing"), ("role_evidence", "role_evidence_missing"),
    ("language", "explanation_language_invalid"), ("missing_language", "missing_facts_language_invalid"),
    ("quote_unique", "edit_quote_not_unique"), ("overlap", "edit_spans_overlap"),
    ("draft", "draft_invalid"),
])
def test_each_review_guard_retains_fixed_reason(kind, reason):
    raw, source, jd = review_payload(with_jd=kind == "role_evidence"), RESUME, ""
    if kind == "schema": raw["extra"] = PRIVATE
    elif kind == "dimensions": raw["dimensions"][-1]["key"] = "completeness"
    elif kind == "evidence": raw["suggestions"][0]["evidence"][0]["quote"] = PRIVATE
    elif kind == "role_evidence":
        jd = JD
        raw["dimensions"][-1]["evidence"] = [{"source": "resume", "quote": "Python"}]
    elif kind == "language": raw["suggestions"][0]["title"] = PRIVATE
    elif kind == "missing_language": raw["missingFacts"] = [PRIVATE]
    elif kind == "quote_unique": source += "\n" + QUOTE
    elif kind == "overlap": raw["edits"] = [{"sourceQuote": "开发数据接口", "replacement": "实现数据接口开发"}, {"sourceQuote": QUOTE, "replacement": "使用Python实现数据接口开发"}]
    elif kind == "draft": source += "\n<script>" + PRIVATE + "</script>"
    assert_failure(lambda: validate_resume_review(raw, resume=source, jd=jd), reason)


def test_private_validation_values_are_not_in_captured_logs(caplog):
    raw = deepcopy(review_payload())
    raw["dimensions"][0]["score"] = PRIVATE
    assert_failure(lambda: validate_resume_review(raw, resume=RESUME + "\n" + PRIVATE, jd=""), "review_schema_invalid")
    assert PRIVATE not in caplog.text


JSON_COMPAT_CASES = [json.loads(line) for line in
    (REPO_ROOT / "ai/evals/cn-resume-optimizer-json-compat-v1.jsonl").read_text().splitlines()
    if line.strip()]


@pytest.mark.parametrize("case", JSON_COMPAT_CASES, ids=[case["id"] for case in JSON_COMPAT_CASES])
def test_strict_json_compatibility_offline_evals(case):
    assert case["synthetic"] is True
    provider, requests = generate_response(content=case["content"], finish=case["finishReason"])
    run = lambda: asyncio.run(provider.generate(resume=case["resume"], jd=case["jd"], target_role=""))
    if case["expectedAccepted"]:
        review, draft = run()
        assert review["overallScore"] == 72 and "synthetic@example.invalid" in draft
    else:
        assert_failure(run, case["expectedReason"])
    assert len(requests) == 1


GROUNDING_CASES = [json.loads(line) for line in
    (REPO_ROOT / "ai/evals/cn-resume-optimizer-v1.jsonl").read_text().splitlines()
    if line.strip()]


@pytest.mark.parametrize("case", GROUNDING_CASES, ids=[case["id"] for case in GROUNDING_CASES])
def test_every_existing_grounding_eval_keeps_its_outcome_inside_json_wrapper(case):
    content = "\ufeff \n```json\n" + json.dumps(case["output"], ensure_ascii=False) + "\n```"
    provider, requests = generate_response(content=content)
    run = lambda: asyncio.run(provider.generate(resume=case["resume"], jd=case["jd"], target_role=""))
    if case["expectedAccepted"]:
        assert run() == validate_resume_review(case["output"], resume=case["resume"], jd=case["jd"])
    else:
        with pytest.raises(ResumeProviderError) as caught:
            run()
        assert caught.value.category == "invalid_output"
        assert normalize_failure_diagnostic(caught.value.diagnostic) is not None
    assert len(requests) == 1
