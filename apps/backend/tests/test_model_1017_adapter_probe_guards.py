"""Offline regressions for probe mistakes; never run remote or provider code."""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

import pytest

from app.core.config import REPO_ROOT, Settings


def load_script(name):
    namespace = {"__name__": "offline_probe_regression"}
    path = Path(REPO_ROOT) / "scripts" / name
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    return namespace


RUNNER = load_script("probe_model_1017_adapters.py")
GATEWAY = load_script("model_1017_gateway_cases.py")
BUSINESS = load_script("model_1017_business_cases.py")


@pytest.mark.parametrize(("group", "only"), [
    ("gateway", []),
    ("gateway", ["web_search_cn", "web_search_cn"]),
    ("gateway", ["vision_four_ordered_global"]),
    ("gateway", ["unknown_operation"]),
    ("gateway", "web_search_cn"),
    ("gateway", [None]),
    ("business", ["resume_cn"]),
    ("business", []),
])
def test_only_rejects_invalid_or_business_selections(group, only):
    with pytest.raises(ValueError):
        RUNNER["bundle"]("cn", "backend", group, only=only)


@pytest.mark.parametrize(("region", "selection", "expected"), [
    ("global", ["vision_four_ordered_global", "vision_single_arithmetic_global"],
     ["vision_single_arithmetic_global", "vision_four_ordered_global"]),
    ("cn", ["web_search_cn"], ["web_search_cn"]),
])
def test_subset_calls_only_selected_cases_before_any_side_effect(region, selection, expected, monkeypatch):
    calls = []
    def record(operation):
        calls.append(operation)
        return {"operation": operation}
    monkeypatch.setitem(GATEWAY, "_chat_case", lambda settings, stage: record("chat_" + stage + "_" + region))
    monkeypatch.setitem(GATEWAY, "_vision_case", lambda settings, four: record(("vision_four_ordered" if four else "vision_single_arithmetic") + "_" + region))
    monkeypatch.setitem(GATEWAY, "_web_case", lambda settings: record("web_search_cn"))
    settings = SimpleNamespace(product_edition=region, **dict.fromkeys(
        ("chat_qwen_model", "chat_quick_model", "chat_detail_model", "screenshot_vision_model"), GATEWAY["TARGET_MODEL"]))
    result = list(GATEWAY["run_gateway_cases"](settings, operations=selection))
    assert calls == expected == [row["operation"] for row in result]
    assert RUNNER["expected_operations"](region, "backend", "gateway", only=selection) == expected
    calls.clear()
    rejected = list(GATEWAY["run_gateway_cases"](settings, operations=[]))
    assert calls == [] and rejected[0]["passed"] is False


@pytest.mark.parametrize(("region", "group"), [("cn", "gateway"), ("global", "gateway"), ("cn", "business"), ("global", "business")])
def test_success_requires_every_operation_specific_check(region, group):
    operations = RUNNER["expected_operations"](region, "backend", group)
    namespace = {"math": math, "TARGET": RUNNER["TARGET"], "CHECK_KEYS": RUNNER["GATEWAY_CHECKS"] if group == "gateway" else RUNNER["BUSINESS_CHECKS"],
        "SAFE_ERRORS": RUNNER["ERRORS"], "SAFE_REASONS": RUNNER["REASONS"],
        "REQUIRED_CHECKS": {operation: RUNNER["required_checks"](operation) for operation in operations}}
    # Compile only pure validators. The remote Docker main is never executed.
    functions = [node for node in ast.parse(RUNNER["REMOTE_TEMPLATE"]).body
                 if isinstance(node, ast.FunctionDef) and node.name in {"number", "validate_row"}]
    exec(compile(ast.Module(body=functions, type_ignores=[]), "pure_probe_validators.py", "exec"), namespace)
    for operation in operations:
        keys = RUNNER["required_checks"](operation)
        valid = {"operation": operation, "model": RUNNER["TARGET"], "syntheticOnly": True, "passed": True,
            "errorType": None, "diagnosticReason": None, "seconds": .01, "checks": dict.fromkeys(keys, True)}
        assert namespace["validate_row"](valid, operation)
        for missing in keys:
            assert not namespace["validate_row"]({**valid, "checks": dict.fromkeys(keys - {missing}, True)}, operation), (operation, missing)
        assert not namespace["validate_row"]({**valid, "checks": {"adapterCompleted": True}}, operation)


@pytest.mark.parametrize(("text", "expected", "accepted"), [
    ("Answer: 42\n\n17 + 25 = 42.", "42", True),
    ("Answer: **42**\n\nThe arithmetic is complete.", "42", True),
    ("**Answer:** **42**\n\nThe arithmetic is complete.", "42", True),
    ("Answer: 7319\n\nThe captured pages are in order.", "7319", True),
    ("The result is 42.", "42", False),
    ("Answer: 41", "42", False),
    ("Answer: 42\n\nThe correct answer is 41.", "42", False),
    ("Answer: 42\n\n42 is incorrect.", "42", False),
    ("Answer: 42.0", "42", False),
    ("Answer: -42", "42", False),
    ("Answer: 4**2", "42", False),
    ("Answer: 7`3`19", "7319", False),
    ("Answer: 7319\nAnswer: 7391", "7319", False),
])
def test_global_original_nonsection_contract_uses_one_unambiguous_answer_line(text, expected, accepted):
    assert GATEWAY["_correct_image_result"](text, expected, "en-US", requires_sections=False) is accepted


def test_global_vision_case_follows_loaded_prompt_without_inventing_two_sections(monkeypatch):
    from app.services import screenshot_answer_service as module
    class OfflineGlobalGateway(module.OpenAICompatibleVisionGateway):
        def _load_system_prompt(self, interview_language="en-US"):
            return "You are a careful coding assistant. Give a direct answer based on the image."

        def stream_analyze(self, **kwargs):
            self._request_payload(instruction=kwargs["instruction"], images=kwargs["images"], stream=True, interview_language="en-US")
            event = {"choices": [{"delta": {"content": "Answer: 42"}, "finish_reason": "stop"}]}
            yield self._extract_stream_text("data: " + json.dumps(event))

    monkeypatch.setattr(module, "OpenAICompatibleVisionGateway", OfflineGlobalGateway)
    monkeypatch.setitem(GATEWAY, "_image", lambda *args: SimpleNamespace(content_type="image/jpeg", payload_bytes=b"\xff\xd8synthetic-only", public_url=None))
    settings = Settings(_env_file=None, environment="test", product_edition="global", **dict.fromkeys(
        ("chat_qwen_model", "chat_quick_model", "chat_detail_model", "screenshot_vision_model"), GATEWAY["TARGET_MODEL"]))
    result = GATEWAY["_vision_case"](settings, False)
    assert result["passed"] is True
    assert result["checks"]["existingOutputContract"] and result["checks"]["syntheticAnswerContract"]


@pytest.mark.parametrize(("text", "accepted"), [
    ("简要回答\n42\n\n---\n\n详细回答\n17 + 25 = 42。", True),
    ("**简要回答**\n**答案：42**\n\n---\n\n**详细回答**\n17 + 25 = 42。", True),
    ("Answer: 42", False),
    ("简要回答\n42\n\n详细回答\n17 + 25 = 42。", False),
    ("简要回答\n42\n\n---\n\n详细回答\n正确答案是41。", False),
    ("简要回答\n4**2\n\n---\n\n详细回答\n算式已经给出。", False),
])
def test_cn_existing_two_section_contract_remains_strict(text, accepted):
    assert GATEWAY["_correct_image_result"](text, "42", "zh-CN", requires_sections=True) is accepted


def test_summary_text_without_provider_stop_cannot_be_reported_as_passed():
    checks = dict.fromkeys(RUNNER["required_checks"]("summary_resume"), True)
    checks["summaryProviderComplete"] = False
    row = BUSINESS["_result"]("summary_resume", monotonic(), checks)
    assert row["checks"]["remoteSummaryReturned"] is True
    assert row["passed"] is False and row["errorType"] == "validation_failed"
    assert row["diagnosticReason"] == "synthetic_checks_failed"
