from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.core.logging import configure_logging
from app.services.integration_verification import (
    IntegrationReportWriter,
    IntegrationVerificationRunner,
    VerificationContext,
    VerificationError,
    VerificationItemResult,
    VerificationItemRecorder,
)


class PassingVerifier:
    item_id = "pass"
    title = "Passing Verifier"
    provider_name = "provider-pass"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        recorder.run_step("ping", lambda: {"ok": True}, success_summary="Ping succeeded.")
        return recorder.finalize(status="passed", attempts=1, summary="Verifier passed.")


class RetryOnceVerifier:
    item_id = "retry"
    title = "Retry Verifier"
    provider_name = "provider-retry"

    def __init__(self) -> None:
        self.calls = 0

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        self.calls += 1
        if self.calls == 1:
            raise VerificationError("retry_once", "Retry once", retryable=True)
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        recorder.run_step("second_try", lambda: {"attempt": self.calls}, success_summary="Succeeded on retry.")
        return recorder.finalize(status="passed", attempts=self.calls, summary="Verifier passed after retry.")


class PartialFailureVerifier:
    item_id = "partial"
    title = "Partial Failure Verifier"
    provider_name = "provider-partial"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        recorder.run_step("first", lambda: {"ok": True}, success_summary="First step passed.")

        def fail() -> dict[str, bool]:
            raise VerificationError("expected_failure", "Expected failure")

        recorder.run_step("second", fail, success_summary="Should not succeed.")
        return recorder.finalize(status="passed", attempts=1, summary="Unexpected pass.")


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        integration_report_output_dir=str(tmp_path / "reports"),
        integration_environment_label="test",
        integration_retry_attempts=1,
    )


def test_runner_supports_targeted_execution_and_retry(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    runner = IntegrationVerificationRunner(
        settings=settings,
        logger=configure_logging(settings),
        verifiers={
            "pass": PassingVerifier(),
            "retry": RetryOnceVerifier(),
        },
    )

    report = runner.run(selected_items=["retry"])

    assert report.overall_status == "passed"
    assert report.selected_items == ["retry"]
    assert len(report.results) == 1
    assert report.results[0].item_id == "retry"
    assert report.results[0].attempts == 2
    assert report.results[0].steps[0].name == "second_try"


def test_report_writer_outputs_json_and_markdown(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    runner = IntegrationVerificationRunner(
        settings=settings,
        logger=configure_logging(settings),
        verifiers={"pass": PassingVerifier()},
    )
    report = runner.run()
    writer = IntegrationReportWriter(output_dir=Path(settings.integration_report_output_dir))

    paths = writer.write(report)

    assert paths["json"].exists()
    assert paths["markdown"].exists()

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["overallStatus"] == "passed"
    assert payload["summary"]["passed"] == 1
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Integration Report" in markdown
    assert "Passing Verifier" in markdown


def test_runner_preserves_completed_steps_on_failure(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    runner = IntegrationVerificationRunner(
        settings=settings,
        logger=configure_logging(settings),
        verifiers={"partial": PartialFailureVerifier()},
    )

    report = runner.run()

    assert report.overall_status == "failed"
    assert report.results[0].status == "failed"
    assert [step.name for step in report.results[0].steps] == ["first", "second"]
    assert report.results[0].steps[0].status == "passed"
    assert report.results[0].steps[1].status == "failed"
