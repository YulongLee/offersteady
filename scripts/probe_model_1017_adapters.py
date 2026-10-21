"""Emit a secret-free, pinned-container adapter probe for reviewed SSH use.

Only --bundle emits remote code. This local tool never contacts a server, runs
Docker, changes configuration or invokes a model. Helpers remain separate exec
namespaces so their private globals cannot overwrite each other.
"""
from __future__ import annotations

import argparse
from pathlib import Path


TARGET = "deepseek-v4.1-flash-1017"
PINS = {
    ("cn", "backend"): ("compose-backend-1", "sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88"),
    ("cn", "worker"): ("compose-material-worker-1", "sha256:df6b8500500e955aa2f01c3bc0c5b40dab218296459f4e8341da268bb6b0ee43"),
    ("global", "backend"): ("offersteady-global-backend-1", "sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19"),
    ("global", "worker"): ("offersteady-global-material-worker-1", "sha256:73624b44e619f6090249798047701c59ed0381d793c1302b59078349707f3010"),
}
SUMMARY_SHA = "d39dd68755db41cf24f6232af57e1615dbf1166e3a497af6e58a92ea1a5821cc"
SUMMARY_OLD = '            "model": self.settings.chat_qwen_model,\n            "stream": False,\n            "temperature": 0.1,'
SUMMARY_NEW = '            "model": self.settings.chat_qwen_model,\n            "stream": False,\n            "enable_thinking": False,\n            "temperature": 0.1,'

BUSINESS_CHECKS = {
    "providerAndExistingValidatorsCompleted", "expectedDimensions", "scoreIsBoundedInteger", "roleMatchAssessed",
    "literalSourceEvidence", "contactPreserved", "sourceNumbersPreserved", "sourceSkillsPreserved", "jdSkillNotInserted",
    "safeSubstantiveEditApplied", "singleQuestion", "questionAndFocusNonempty", "groundedInSyntheticSkills",
    "contactNotRepeated", "oneConfirmedAnswerFeedback", "literalAnswerQuote", "serverAnswerStructureUsed",
    "partialReportDisclosed", "remoteSummaryReturned", "existingPrefixAndLimit", "sourceSkillsRetained", "noInventedNumbers",
    "summaryCandidateNonThinkingRequest", "summaryProviderComplete",
}
GATEWAY_CHECKS = {
    "candidateModelAndRegionConfigured", "adapterCompleted", "oneCandidateNonThinkingStream", "providerStop",
    "nonemptyAnswer", "sessionLanguage", "syntheticFactsRetained", "noInventedPercentage", "normalizedQuestionFirst",
    "oneCandidateOrderedNonThinkingStream", "existingJpegOptimization", "existingOutputContract", "syntheticAnswerContract",
    "correctImageOnlyResult", "resultNotLeakedInInstruction", "actualSearchSucceeded", "noLocalFallbackCountedAsSearch",
    "oneCandidateNonThinkingSearch", "sourceLinksReturned", "publicPythonSource",
    "webSearchExecutionCompleted", "appendExtendSemantics",
    "requestedOperationsValid",
}
ERRORS = {
    "invalid_output", "provider_timeout", "provider_unavailable", "provider_unconfigured", "interrupted", "source_unavailable",
    "adapter_error", "adapter_unavailable", "mock_generation_unavailable", "validation_failed",
}
REASONS = {
    "unclassified_adapter_failure", "synthetic_checks_failed", "provider_timeout", "provider_http_error", "provider_unconfigured",
    "response_too_large", "response_encoding_invalid", "provider_envelope_invalid", "provider_finish_length", "provider_finish_invalid",
    "content_encoding_invalid", "content_json_invalid", "content_json_ambiguous", "review_schema_invalid", "dimension_set_invalid",
    "evidence_quote_missing", "role_evidence_missing", "explanation_language_invalid", "missing_facts_language_invalid",
    "edit_quote_not_unique", "fact_numbers_changed", "fact_contact_changed", "fact_english_content_added", "fact_english_content_removed",
    "fact_credentials_changed", "fact_dates_counts_changed", "fact_negation_changed", "fact_entities_changed", "fact_responsibility_changed",
    "fact_skills_changed", "edit_spans_overlap", "draft_invalid", "no_effective_edits", "slot_wait_timeout", "provider_transport_error",
    "context_limit", "response_json_invalid", "incomplete_response", "response_envelope_invalid", "structured_output_invalid",
    "question_schema_invalid", "report_schema_invalid", "report_evidence_invalid", "repeated_question", "internal_error",
    "bounded_request_timeout", "runtime_adapter_unavailable", "adapter_request_failed", "chat_provider_unavailable",
    "chat_provider_rate_limited", "chat_provider_auth_failed", "chat_provider_request_rejected", "chat_config_missing",
    "chat_provider_invalid_response", "web_search_not_configured", "web_search_auth_failed", "web_search_rate_limited",
    "web_search_provider_rejected", "web_search_empty_result", "web_search_provider_unavailable",
}


def expected_operations(region, component, group, *, only=None):
    if group == "business":
        if only is not None:
            raise ValueError("operation_selection_requires_gateway")
        prefix = [] if component == "worker" else (["resume_cn", "resume_cn_no_jd", "mock_question_cn", "mock_report_cn"] if region == "cn" else ["resume_global", "resume_global_no_jd"])
        return prefix + ["summary_resume", "summary_job_description"]
    if component != "backend":
        raise ValueError("gateway_requires_backend")
    suffix = "_" + region
    known = [name + suffix for name in ("chat_quick", "chat_detail", "vision_single_arithmetic", "vision_four_ordered")] + (["web_search_cn"] if region == "cn" else [])
    if only is None:
        return known
    if type(only) not in (list, tuple) or not only or any(type(operation) is not str for operation in only):
        raise ValueError("operation_selection_invalid")
    if len(set(only)) != len(only) or not set(only) <= set(known):
        raise ValueError("operation_selection_unknown_or_duplicate")
    return [operation for operation in known if operation in only]


def required_checks(operation):
    if operation.startswith("resume_"):
        common = {"providerAndExistingValidatorsCompleted", "expectedDimensions", "scoreIsBoundedInteger", "roleMatchAssessed",
                  "literalSourceEvidence", "contactPreserved", "sourceNumbersPreserved", "sourceSkillsPreserved", "jdSkillNotInserted"}
        return common | ({"safeSubstantiveEditApplied"} if operation.startswith("resume_cn") else set())
    if operation == "mock_question_cn":
        return {"providerAndExistingValidatorsCompleted", "singleQuestion", "questionAndFocusNonempty", "groundedInSyntheticSkills", "contactNotRepeated"}
    if operation == "mock_report_cn":
        return {"providerAndExistingValidatorsCompleted", "scoreIsBoundedInteger", "oneConfirmedAnswerFeedback", "literalAnswerQuote", "serverAnswerStructureUsed", "partialReportDisclosed"}
    if operation.startswith("summary_"):
        return {"remoteSummaryReturned", "summaryCandidateNonThinkingRequest", "summaryProviderComplete", "existingPrefixAndLimit", "sourceSkillsRetained", "noInventedNumbers"}
    if operation.startswith("chat_"):
        common = {"adapterCompleted", "oneCandidateNonThinkingStream", "providerStop", "nonemptyAnswer", "sessionLanguage", "syntheticFactsRetained", "noInventedPercentage"}
        return common | ({"normalizedQuestionFirst"} if operation.startswith("chat_quick_") else set())
    if operation.startswith("vision_"):
        return {"adapterCompleted", "oneCandidateOrderedNonThinkingStream", "existingJpegOptimization", "providerStop", "nonemptyAnswer", "sessionLanguage", "existingOutputContract", "syntheticAnswerContract", "correctImageOnlyResult", "resultNotLeakedInInstruction"}
    if operation == "web_search_cn":
        return {"actualSearchSucceeded", "webSearchExecutionCompleted", "appendExtendSemantics", "noLocalFallbackCountedAsSearch", "oneCandidateNonThinkingSearch", "nonemptyAnswer", "sourceLinksReturned", "publicPythonSource"}
    raise ValueError("unknown_case_operation")


INNER_TEMPLATE = r'''
import asyncio, contextlib, hashlib, importlib.util, io, json, logging, sys, types
from pathlib import Path
logging.disable(logging.CRITICAL)
out = {"results": [], "candidateSummaryPatchApplied": False, "candidateSelectorsScoped": False,
       "liveSettingsUnchanged": False, "liveSourceUnchanged": True, "depsNotImported": False,
       "unexpectedOutput": False, "errorType": None}
captured_out, captured_err = io.StringIO(), io.StringIO()
class ProbeInvariantError(Exception):
    pass
try:
    with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
        from app.core.config import Settings
        live = Settings()
        before_settings = live.model_dump(mode="json")
        fields = type(live).model_fields
        required = ("chat_qwen_model", "chat_quick_model", "chat_detail_model", "screenshot_vision_model") if COMPONENT == "backend" else ("chat_qwen_model",)
        if not all(name in fields for name in required):
            raise ProbeInvariantError("candidate_settings_missing")
        updates = {name: TARGET for name in required}
        if COMPONENT == "worker" and REGION == "cn":
            updates.update({name: TARGET for name in ("chat_quick_model", "chat_detail_model") if name in fields})
        candidate = live.model_copy(update=updates)
        after_candidate = candidate.model_dump(mode="json")
        out["candidateSelectorsScoped"] = all(after_candidate.get(key) == (TARGET if key in updates else value) for key, value in before_settings.items()) and set(after_candidate) == set(before_settings)
        if not out["candidateSelectorsScoped"]:
            raise ProbeInvariantError("candidate_settings_scope_failed")
        summary_path = None
        if REGION == "global" and GROUP == "business":
            module_name = "app.services.document_processing"
            spec = importlib.util.find_spec(module_name)
            if spec is None or not spec.origin or module_name in sys.modules:
                raise ProbeInvariantError("candidate_summary_import_order_failed")
            summary_path = Path(spec.origin)
            original_bytes = summary_path.read_bytes()
            if hashlib.sha256(original_bytes).hexdigest() != SUMMARY_SHA:
                raise ProbeInvariantError("candidate_summary_source_drift")
            original = original_bytes.decode("utf-8")
            if original.count(SUMMARY_OLD) != 1:
                raise ProbeInvariantError("candidate_summary_snippet_mismatch")
            patched = original.replace(SUMMARY_OLD, SUMMARY_NEW, 1)
            compiled = compile(patched, str(summary_path), "exec")
            module = types.ModuleType(module_name)
            module.__file__, module.__package__, module.__spec__, module.__loader__ = str(summary_path), "app.services", spec, spec.loader
            sys.modules[module_name] = module
            exec(compiled, module.__dict__)
            setattr(sys.modules["app.services"], "document_processing", module)
            out["candidateSummaryPatchApplied"] = True
        source = GATEWAY_SOURCE if GROUP == "gateway" else BUSINESS_SOURCE
        namespace = {"__name__": "synthetic_model_1017_cases"}
        exec(compile(source, "synthetic_model_1017_cases.py", "exec"), namespace)
        if "app.deps" in sys.modules:
            raise ProbeInvariantError("deps_imported")
        if GROUP == "gateway":
            out["results"] = list(namespace["run_gateway_cases"](candidate, operations=OPERATIONS))
        else:
            out["results"] = asyncio.run(namespace["run_business_cases"](candidate, worker_only=COMPONENT == "worker"))
        out["liveSettingsUnchanged"] = Settings().model_dump(mode="json") == before_settings and live.model_dump(mode="json") == before_settings
        out["depsNotImported"] = "app.deps" not in sys.modules
        if summary_path is not None:
            out["liveSourceUnchanged"] = hashlib.sha256(summary_path.read_bytes()).hexdigest() == SUMMARY_SHA
except ProbeInvariantError as error:
    # The only source of this argument is the fixed literals above.
    out["errorType"] = error.args[0]
except Exception:
    out["errorType"] = "adapter_probe_failed"
out["unexpectedOutput"] = bool(captured_out.getvalue() or captured_err.getvalue())
meta_passed = out["candidateSelectorsScoped"] and out["liveSettingsUnchanged"] and out["liveSourceUnchanged"] and out["depsNotImported"] and not out["unexpectedOutput"] and out["errorType"] is None
rows = out["results"]
passed = meta_passed and type(rows) is list and bool(rows) and all(type(row) is dict and row.get("passed") is True for row in rows)
print(json.dumps(out, ensure_ascii=True, allow_nan=False), flush=True)
raise SystemExit(0 if passed else 1)
'''


REMOTE_TEMPLATE = r'''
import hashlib, json, math, re, subprocess, sys
def fail(label):
    print(json.dumps({"region": REGION, "component": COMPONENT, "group": GROUP, "kind": "verification", "passed": False, "errorType": label, "productionChanged": False}), flush=True)
    raise SystemExit(2)
def inspect(name):
    result = subprocess.run(["docker", "inspect", name], capture_output=True, text=True, timeout=15)
    if result.returncode or len(result.stdout) > 2 * 1024 * 1024:
        raise ValueError("inspect_failed")
    values = json.loads(result.stdout)
    if type(values) is not list or len(values) != 1:
        raise ValueError("inspect_failed")
    return values[0]
def frozen(value):
    return {key: value.get(key) for key in ("Id", "Image", "Config", "HostConfig", "Mounts")} | {"startedAt": value.get("State", {}).get("StartedAt"), "running": value.get("State", {}).get("Running"), "restartCount": value.get("RestartCount")}
def number(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum
def validate_row(row, expected):
    required = {"operation", "model", "syntheticOnly", "passed", "errorType", "diagnosticReason", "seconds", "checks"}
    if type(row) is not dict or not required <= set(row) or set(row) - required - {"firstTextMs"}:
        return False
    if row["operation"] != expected or row["model"] != TARGET or row["syntheticOnly"] is not True or type(row["passed"]) is not bool:
        return False
    if not number(row["seconds"], 600) or (row.get("firstTextMs") is not None and not number(row["firstTextMs"], 600000)):
        return False
    checks = row["checks"]
    if type(checks) is not dict or not checks or not set(checks) <= CHECK_KEYS or not all(type(value) is bool for value in checks.values()):
        return False
    if not set(checks) <= REQUIRED_CHECKS[expected] or (row["passed"] and set(checks) != REQUIRED_CHECKS[expected]):
        return False
    if row["errorType"] is not None and (type(row["errorType"]) is not str or row["errorType"] not in SAFE_ERRORS):
        return False
    if row["diagnosticReason"] is not None and (type(row["diagnosticReason"]) is not str or row["diagnosticReason"] not in SAFE_REASONS):
        return False
    if row["passed"] and (not all(checks.values()) or row["errorType"] is not None or row["diagnosticReason"] is not None):
        return False
    if not row["passed"] and row["errorType"] is None:
        return False
    return True
try:
    before = inspect(CONTAINER)
except Exception:
    fail("container_inspection_failed")
if before.get("Image") != PINNED_IMAGE or not re.fullmatch(r"[a-f0-9]{64}", before.get("Id", "")) or before.get("State", {}).get("Running") is not True:
    fail("runtime_image_or_state_drift")
immutable_id = before["Id"]
try:
    result = subprocess.run(["docker", "exec", "-i", "-w", "/app/apps/backend", immutable_id, "python", "-B", "-"], input=INNER, capture_output=True, text=True, timeout=480)
except Exception:
    fail("probe_process_failed")
try:
    after = inspect(CONTAINER)
except Exception:
    fail("post_probe_inspection_failed")
container_unchanged = frozen(before) == frozen(after)
if not container_unchanged:
    fail("runtime_changed_during_probe")
if result.stderr or len(result.stdout) > 131072:
    fail("unexpected_probe_output")
try:
    payload = json.loads(result.stdout)
except Exception:
    fail("invalid_probe_envelope")
allowed_meta = {"results", "candidateSummaryPatchApplied", "candidateSelectorsScoped", "liveSettingsUnchanged", "liveSourceUnchanged", "depsNotImported", "unexpectedOutput", "errorType"}
if type(payload) is not dict or set(payload) != allowed_meta:
    fail("invalid_probe_envelope")
meta_flags = allowed_meta - {"results", "errorType"}
if not all(type(payload[key]) is bool for key in meta_flags):
    fail("invalid_probe_envelope")
safe_inner_errors = {"candidate_settings_missing", "candidate_settings_scope_failed", "candidate_summary_import_order_failed", "candidate_summary_source_drift", "candidate_summary_snippet_mismatch", "deps_imported", "adapter_probe_failed"}
if payload["errorType"] is not None and (type(payload["errorType"]) is not str or payload["errorType"] not in safe_inner_errors):
    fail("invalid_probe_envelope")
if payload["errorType"] is not None:
    fail(payload["errorType"])
rows = payload["results"]
if type(rows) is not list or len(rows) != len(EXPECTED) or not all(validate_row(row, operation) for row, operation in zip(rows, EXPECTED)):
    fail("invalid_or_missing_case_results")
expected_patch = REGION == "global" and GROUP == "business"
meta_passed = payload["candidateSummaryPatchApplied"] is expected_patch and payload["candidateSelectorsScoped"] and payload["liveSettingsUnchanged"] and payload["liveSourceUnchanged"] and payload["depsNotImported"] and not payload["unexpectedOutput"]
passed = meta_passed and all(row["passed"] for row in rows)
if result.returncode != (0 if passed else 1):
    fail("probe_exit_inconsistent")
for row in rows:
    print(json.dumps({"region": REGION, "component": COMPONENT, "group": GROUP, "kind": "case", **row}, ensure_ascii=True, allow_nan=False), flush=True)
print(json.dumps({"region": REGION, "component": COMPONENT, "group": GROUP, "kind": "verification", "passed": passed,
    "checks": len(rows), "candidateSummaryPatchApplied": payload["candidateSummaryPatchApplied"],
    "candidateSelectorsScoped": payload["candidateSelectorsScoped"], "liveSettingsUnchanged": payload["liveSettingsUnchanged"],
    "liveContainerConfigUnchanged": container_unchanged, "liveSourceUnchanged": payload["liveSourceUnchanged"],
    "depsNotImported": payload["depsNotImported"], "productionChanged": False}, sort_keys=True), flush=True)
raise SystemExit(0 if passed else 1)
'''


def bundle(region, component, group, *, directory=None, only=None):
    expected = expected_operations(region, component, group, only=only)
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent
    business_source = (directory / "model_1017_business_cases.py").read_text(encoding="utf-8")
    gateway_source = (directory / "model_1017_gateway_cases.py").read_text(encoding="utf-8")
    compile(business_source, "model_1017_business_cases.py", "exec")
    compile(gateway_source, "model_1017_gateway_cases.py", "exec")
    shared = {"REGION": region, "COMPONENT": component, "GROUP": group, "TARGET": TARGET}
    inner_values = {**shared, "OPERATIONS": tuple(expected) if group == "gateway" else None,
                    "SUMMARY_SHA": SUMMARY_SHA, "SUMMARY_OLD": SUMMARY_OLD, "SUMMARY_NEW": SUMMARY_NEW,
                    "BUSINESS_SOURCE": business_source, "GATEWAY_SOURCE": gateway_source}
    inner = "\n".join(f"{key} = {value!r}" for key, value in inner_values.items()) + "\n" + INNER_TEMPLATE
    container, image = PINS[(region, component)]
    outer_values = {**shared, "CONTAINER": container, "PINNED_IMAGE": image, "INNER": inner, "EXPECTED": expected,
                    "CHECK_KEYS": BUSINESS_CHECKS if group == "business" else GATEWAY_CHECKS,
                    "SAFE_ERRORS": ERRORS, "SAFE_REASONS": REASONS,
                    "REQUIRED_CHECKS": {operation: required_checks(operation) for operation in expected}}
    source = "\n".join(f"{key} = {value!r}" for key, value in outer_values.items()) + "\n" + REMOTE_TEMPLATE
    compile(source, "probe_model_1017_remote.py", "exec")
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="store_true", required=True)
    parser.add_argument("--region", choices=("cn", "global"), required=True)
    parser.add_argument("--component", choices=("backend", "worker"), required=True)
    parser.add_argument("--group", choices=("gateway", "business"), required=True)
    parser.add_argument("--only", nargs="+", help="Run only these known gateway operations, in canonical order.")
    args = parser.parse_args()
    if args.component == "worker" and args.group == "gateway":
        parser.error("gateway probes require --component backend")
    try:
        source = bundle(args.region, args.component, args.group, only=args.only)
    except ValueError as error:
        parser.error(str(error))
    print(source)


if __name__ == "__main__":
    main()
