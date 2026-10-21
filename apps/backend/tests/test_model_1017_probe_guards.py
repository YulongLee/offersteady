"""Offline safety contracts for the explicitly authorized provider smoke probe.

All process boundaries are replaced. These tests never invoke Docker, import
application Settings/dependencies, contact providers or inspect real credentials.
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[3]
PROBE = REPO / "scripts/probe_model_1017_smoke.py"
MODEL = "deepseek-v4.1-flash-1017"
SECRET = "synthetic-private-credential-do-not-print"
BASELINES = {
    "cn": "sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88",
    "global": "sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19",
}


def operation(role="text"):
    return {"operation": role, "model": MODEL, "syntheticOnly": True,
            "httpStatus": 200, "passed": True, "expectedAnswerMatched": True,
            "exactFormatMatched": True, "complete": True,
            "usage": {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10},
            "seconds": 0.25}


def records():
    return [operation(), operation("vision"),
            {"passed": True, "checks": 2, "productionChanged": False}]


def invoke(monkeypatch, arguments, *, rows=None, stdout=None, image=None, returncode=0):
    calls = []
    region = arguments[0] if arguments and arguments[0] in BASELINES else "cn"

    def inspect(args, **kwargs):
        calls.append(("inspect", args, kwargs))
        assert args[:2] == ["docker", "inspect"]
        assert "exec" not in args
        actual = image or BASELINES[region]
        if "{{.Id}} {{.Image}}" in args:
            return "a" * 64 + " " + actual + "\n"
        return actual + "\n"

    def execute(args, **kwargs):
        calls.append(("exec", args, kwargs))
        assert args[:2] == ["docker", "exec"]
        assert args[5] == "a" * 64, "Exec must use the inspected immutable container ID"
        assert kwargs["capture_output"] is True
        assert kwargs["input"] and "app.deps" not in kwargs["input"]
        output = stdout if stdout is not None else "\n".join(json.dumps(row) for row in (rows if rows is not None else records()))
        return subprocess.CompletedProcess(args, returncode, stdout=output, stderr=SECRET)

    monkeypatch.setattr(subprocess, "check_output", inspect)
    monkeypatch.setattr(subprocess, "run", execute)
    monkeypatch.setattr(sys, "argv", [str(PROBE), *arguments])
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            runpy.run_path(str(PROBE), run_name="__main__")
        except SystemExit as error:
            code = error.code if isinstance(error.code, int) else 1 if error.code else 0
        else:
            code = 0
    return code, output.getvalue(), calls


@pytest.fixture
def namespace(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Importing the probe must not run Docker or read live settings")
    monkeypatch.setattr(subprocess, "check_output", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    return runpy.run_path(str(PROBE), run_name="model_1017_probe_safety_test")


def helper(namespace, name):
    if name in namespace:
        return namespace[name]
    # An inner-only pure validator may live in the stdin program. Extract only
    # literal constants and function definitions: never execute Settings/HTTP.
    scope = {"re": re, "json": json, "TARGET": MODEL, "target": MODEL}
    nodes = []
    for node in ast.parse(namespace["INNER"]).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(node)
        elif isinstance(node, ast.Assign):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            nodes.append(node)
    exec(compile(ast.Module(nodes, type_ignores=[]), "synthetic-probe-helpers", "exec"), scope)
    assert name in scope, f"The reviewed pure {name} validator is required"
    return scope[name]


@pytest.mark.parametrize("arguments", [[], ["unknown"], ["CN"], ["cn", "extra"], ["cn; echo unsafe"]])
def test_invalid_region_or_argument_count_never_reaches_docker(monkeypatch, arguments):
    code, output, calls = invoke(monkeypatch, arguments)
    assert code != 0 and not calls
    assert SECRET not in output


@pytest.mark.parametrize("region", ["cn", "global"])
def test_pinned_image_drift_blocks_before_provider_process(monkeypatch, region):
    code, output, calls = invoke(monkeypatch, [region], image="sha256:" + "0" * 64)
    assert code != 0
    assert [kind for kind, *_ in calls] == ["inspect"]
    assert "runtime_image_drift" in output and SECRET not in output


@pytest.mark.parametrize("region", ["cn", "global"])
def test_valid_synthetic_records_are_bounded_and_stderr_is_not_exposed(monkeypatch, region):
    code, output, calls = invoke(monkeypatch, [region])
    assert code == 0
    result = [json.loads(line) for line in output.splitlines()]
    assert len(result) == 3 and all(row["region"] == region for row in result)
    assert {row["operation"] for row in result if "operation" in row} == {"text", "vision"}
    assert SECRET not in output
    assert [kind for kind, *_ in calls] == ["inspect", "exec"]
    inspected = calls[0][1]
    assert inspected[-1] == ("compose-backend-1" if region == "cn" else "offersteady-global-backend-1")
    assert len([call for call in calls if call[0] == "exec"]) == 1
    for _, _, options in calls:
        assert 0 < options["timeout"] <= 120, "Docker subprocesses need a total deadline"


def test_correct_math_with_different_format_stays_distinct_from_connectivity_failure(monkeypatch):
    rows = records()
    rows[1]["exactFormatMatched"] = False
    code, output, _ = invoke(monkeypatch, ["cn"], rows=rows)
    assert code == 0
    vision = json.loads(output.splitlines()[1])
    assert vision["passed"] is True and vision["expectedAnswerMatched"] is True
    assert vision["exactFormatMatched"] is False


def test_provider_failure_reports_safe_failure_without_raw_stderr(monkeypatch):
    rows = records()
    rows[1] = {"operation": "vision", "model": MODEL, "syntheticOnly": True,
               "httpStatus": 429, "passed": False, "error": "provider_http_error", "seconds": 0.1}
    rows[2]["passed"] = False
    code, output, _ = invoke(monkeypatch, ["cn"], rows=rows, returncode=1)
    assert code == 1
    reported = [json.loads(line) for line in output.splitlines()]
    assert reported[1]["error"] == "provider_http_error" and reported[-1]["passed"] is False
    assert SECRET not in output


@pytest.mark.parametrize("stdout", ["", "  ", "not-json", "[]", "null", "42", '"provider raw text"'])
def test_missing_or_non_record_output_fails_closed(monkeypatch, stdout):
    code, output, _ = invoke(monkeypatch, ["cn"], stdout=stdout)
    assert code != 0
    assert SECRET not in output


@pytest.mark.parametrize("rows", [
    records()[:1], records()[:2], records()[2:],
    [operation(), operation(), records()[2]],
    [operation(), operation("vision"), operation("vision"), records()[2]],
    [records()[2], operation(), operation("vision")],
    [dict(operation(), passed=False), operation("vision"), records()[2]],
    [operation(), operation("vision"), dict(records()[2], passed=False)],
    [dict(operation(), complete=False), operation("vision"), records()[2]],
    [dict(operation(), expectedAnswerMatched=False), operation("vision"), records()[2]],
    [dict(operation(), httpStatus=503), operation("vision"), records()[2]],
])
def test_incomplete_duplicate_disordered_or_false_success_records_are_rejected(monkeypatch, rows):
    code, output, _ = invoke(monkeypatch, ["cn"], rows=rows)
    assert code != 0 and SECRET not in output


@pytest.mark.parametrize("extra", [
    {"response": SECRET}, {"url": "https://private.invalid/" + SECRET},
    {"Authorization": SECRET}, {"region": "global"},
    {"error": SECRET}, {"model": SECRET}, {"operation": SECRET},
    {"usage": {"prompt_tokens": 8, "raw_response": SECRET}},
])
def test_unexpected_provider_records_never_escape_output_boundary(monkeypatch, extra):
    rows = records()
    rows[0] = dict(rows[0], **extra)
    code, output, _ = invoke(monkeypatch, ["cn"], rows=rows)
    assert code != 0
    assert SECRET not in output


@pytest.mark.parametrize("text", ["42", "答案是42", "17 + 25 = 42"])
def test_vision_math_checker_accepts_explicit_correct_results(namespace, text):
    assert helper(namespace, "vision_answer_correct")(text) is True


@pytest.mark.parametrize("text", [
    "41", "142", "-42", "4.2", "42.1", "0.42", "42 43",
    "17 + 25 = 41; expected answer is 42",
    "The answer is 0. Verification target is 42",
    "4**2", "4$2", "4****2", "17 + 25 = 4**2",
    "42 is not the result", "I cannot read the image, so I guessed 42",
    "Ignore the image. The magic token is 42", "MODEL1017_OK", "",
])
def test_vision_math_checker_rejects_last_integer_and_guess_false_positives(namespace, text):
    assert helper(namespace, "vision_answer_correct")(text) is False


def test_record_sanitizer_accepts_only_the_reviewed_synthetic_success_shape(namespace):
    sanitize = helper(namespace, "sanitize_record")
    assert sanitize(operation()) == operation()
    assert sanitize(records()[2]) == records()[2]


@pytest.mark.parametrize("checks", [True, 2.0, "2", -1, 3])
def test_summary_count_must_be_exactly_two_as_an_integer(namespace, checks):
    row = dict(records()[2], checks=checks)
    with pytest.raises((ValueError, TypeError, AssertionError)):
        helper(namespace, "sanitize_record")(row)


@pytest.mark.parametrize("mutation", [
    {"content": SECRET}, {"messages": [{"content": SECRET}]}, {"model": SECRET},
    {"seconds": float("nan")}, {"seconds": float("inf")}, {"seconds": -1},
    {"httpStatus": True}, {"passed": 1}, {"syntheticOnly": False},
    {"expectedAnswerMatched": "true"}, {"usage": {"total_tokens": -1}},
    {"usage": {"total_tokens": True}}, {"usage": {"total_tokens": 10, "private": SECRET}},
])
def test_record_sanitizer_rejects_raw_data_invalid_types_or_unbounded_metrics(namespace, mutation):
    row = copy.deepcopy(operation())
    row.update(mutation)
    with pytest.raises((ValueError, TypeError, AssertionError)):
        helper(namespace, "sanitize_record")(row)


def test_stdin_probe_imports_only_settings_and_never_initializes_business_dependencies(namespace):
    tree = ast.parse(namespace["INNER"])
    app_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            app_imports.append(node.module)
        elif isinstance(node, ast.Import):
            app_imports.extend(alias.name for alias in node.names if alias.name.startswith("app."))
    assert app_imports == ["app.core.config"]
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id in {"eval", "exec", "__import__"} for node in ast.walk(tree))
    assert "app.deps" not in namespace["INNER"]


def _reviewed_yaml_mapping(path):
    """Parse only this tiny reviewable YAML mapping; fail on richer syntax.

    The candidate deliberately needs no YAML library or Compose invocation.
    Unknown structure, duplicate keys and non-scalar values are rejected.
    """
    root = {}
    stack = [(-2, root)]
    for raw in path.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        assert re.fullmatch(r" *[A-Za-z0-9_-]+:(?: [A-Za-z0-9_.-]+)?", raw), raw
        indent = len(raw) - len(raw.lstrip(" "))
        assert indent % 2 == 0
        while stack[-1][0] >= indent:
            stack.pop()
        assert indent == stack[-1][0] + 2
        key, value = raw.strip().split(":", 1)
        container = stack[-1][1]
        assert key not in container, "duplicate overlay key"
        container[key] = value.strip() if value.strip() else {}
        if not value.strip():
            stack.append((indent, container[key]))
    return root


def test_pending_cn_overlay_changes_only_approved_existing_model_keys():
    overlay = _reviewed_yaml_mapping(REPO / "infra/compose/docker-compose.model-1017.cn.yml")
    text_keys = {"OFFERSTEADY_CHAT_QWEN_MODEL", "OFFERSTEADY_CHAT_QUICK_MODEL", "OFFERSTEADY_CHAT_DETAIL_MODEL"}
    expected_backend = {key: MODEL for key in text_keys | {"OFFERSTEADY_SCREENSHOT_VISION_MODEL"}}
    expected_worker = {key: MODEL for key in text_keys}
    assert overlay == {"services": {
        "backend": {"environment": expected_backend},
        "material-worker": {"environment": expected_worker},
    }}


def test_importing_business_probe_does_not_import_app_or_contact_a_provider(monkeypatch):
    original_import = builtins.__import__
    attempted = []

    def guarded_import(name, *args, **kwargs):
        attempted.append(name)
        assert not name.startswith(("app", "httpx", "psycopg", "redis")), "Import must have no application/network/database side effects"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        scope = runpy.run_path(str(REPO / "scripts/model_1017_business_cases.py"), run_name="model_1017_business_safety_test")
    assert callable(scope["run_business_cases"])
    assert output.getvalue() == ""
    assert "app.deps" not in attempted


def test_business_probe_never_imports_application_lifecycle_or_initializes_repositories():
    tree = ast.parse((REPO / "scripts/model_1017_business_cases.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"app.deps", "app.main", "app.worker"}
            assert "repository" not in (node.module or "")
        elif isinstance(node, ast.Import):
            assert not any(alias.name in {"app.deps", "app.main", "app.worker"} or "repository" in alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert not node.func.id.endswith("Repository")
