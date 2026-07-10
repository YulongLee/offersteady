from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.core.logging import configure_logging
from app.services.end_to_end_integration import EndToEndIntegrationRunner, EndToEndReportWriter, ScenarioRunner


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        integration_report_output_dir=str(tmp_path / "reports"),
        integration_environment_label="test-e2e",
    )


def test_end_to_end_runner_supports_scenario_only_execution(tmp_path: Path, monkeypatch) -> None:
    settings = build_settings(tmp_path)
    logger = configure_logging(settings)

    def fake_upload(*args, **kwargs):
        return {"httpStatus": 204, "bytes": kwargs["payload"] and len(kwargs["payload"])}

    monkeypatch.setattr(ScenarioRunner, "_upload_via_oss", fake_upload)

    runner = EndToEndIntegrationRunner(settings=settings, logger=logger)
    report = runner.run(skip_providers=True)

    assert report.overall_status == "passed"
    assert report.provider_summary["status"] == "skipped"
    assert report.scenario_summary["passed"] == 4
    assert all(item.status == "passed" for item in report.scenarios)
    assert any(item.scenario_id == "session-chat" for item in report.scenarios)


def test_end_to_end_report_writer_outputs_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    settings = build_settings(tmp_path)
    logger = configure_logging(settings)

    monkeypatch.setattr(ScenarioRunner, "_upload_via_oss", lambda *args, **kwargs: {"httpStatus": 204})

    report = EndToEndIntegrationRunner(settings=settings, logger=logger).run(skip_providers=True)
    writer = EndToEndReportWriter(Path(settings.integration_report_output_dir))

    paths = writer.write(report)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["bug_json"].exists()
    assert paths["bug_markdown"].exists()
    assert paths["todo_json"].exists()
    assert paths["todo_markdown"].exists()

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["overallStatus"] == "passed"
    assert payload["scenarioSummary"]["passed"] == 4

    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "End-to-End Integration Report" in markdown
    assert "Retrieval-backed Interview Session and Chat" in markdown

    bug_payload = json.loads(paths["bug_json"].read_text(encoding="utf-8"))
    assert bug_payload["count"] >= 1
    assert any(item["issueId"] == "frontend-real-state-aggregation-missing" for item in bug_payload["items"])

    todo_payload = json.loads(paths["todo_json"].read_text(encoding="utf-8"))
    assert todo_payload["count"] >= 1
    assert any(item["itemId"] == "ship-prototype-state-api" for item in todo_payload["items"])
