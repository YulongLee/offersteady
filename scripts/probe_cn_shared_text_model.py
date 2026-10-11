"""Explicit, synthetic-only provider probe; never creates sessions or jobs.

Run only on reviewed candidate/runtime images with server-side credentials.
The fixture is synthetic and the output contains no credentials or user data.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
from time import monotonic
from types import SimpleNamespace

sys.path.insert(0, "/app/apps/backend")

from app.core.config import Settings  # noqa: E402
from app.services.document_processing import DocumentProcessingService  # noqa: E402


async def verify(fixtures: list[dict], *, summaries_only: bool) -> list[dict]:
    settings = Settings()
    assert settings.product_edition == "cn", "CN configuration required"
    assert settings.chat_qwen_model == "deepseek-v4.1-flash", "candidate model not configured"
    summary_service = object.__new__(DocumentProcessingService)
    summary_service.settings = settings
    summary_service.logger = logging.getLogger("synthetic-cn-model-probe")
    generator = None
    if not summaries_only:
        # Older, independent material-worker images intentionally omit mock APIs.
        from app.services.mock_interview_generation import MockInterviewGenerator
        from app.services.mock_interview_rounds import MockRound

        generator = MockInterviewGenerator(settings)
    results = []
    for row in fixtures:
        operation = row["operation"]
        if summaries_only and operation != "summary":
            continue
        started = monotonic()
        if operation == "summary":
            document = SimpleNamespace(document_kind=row["document_kind"], document_id=row["id"])
            output = summary_service._try_remote_interview_summary(document=document, clean_text=row["text"])
            assert output and "面试摘要：" in output, "remote summary did not succeed; fallback is not a provider pass"
            assert "PostgreSQL" in output or "Python" in output or "订单" in output, "summary lost fixture facts"
            assert not any(term in output for term in ["提升50%", "提升 50%", "降低90%"]), "invented summary result"
            result = {"id": row["id"], "operation": operation, "output": output}
        else:
            rounds = tuple(MockRound(r["question_id"], r["question"], r.get("answer")) for r in row["rounds"])
            output = await getattr(generator, operation)(resume=row["resume"], target_role=row["role"], rounds=rounds)
            if operation == "question":
                assert len(output.question) <= 800 and output.focus
                assert output.question.count("？") + output.question.count("?") <= 1
                assert any(term in output.question for term in ["订单", "唯一", "幂等", "Python", "PostgreSQL", "Redis"])
                result = {"id": row["id"], "operation": operation, "question": output.question, "focus": output.focus}
            else:
                assert output.dimensions and output.overall_score is not None and len(output.feedback) == len(rounds)
                expected = {r.question_id: r.answer for r in rounds}
                assert all(f.answer_quote in expected[f.question_id] for f in output.feedback)
                assert "1/10" in output.summary
                assert all("没有测量或无法确认" in f.suggestion for f in output.feedback)
                result = {"id": row["id"], "operation": operation, "summary": output.summary,
                          "score": output.overall_score, "evidence": [f.answer_quote for f in output.feedback]}
        result.update(model=settings.chat_qwen_model, passed=True, seconds=round(monotonic() - started, 3))
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--summaries-only", action="store_true")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.fixtures).read_text().splitlines() if line.strip()]
    try:
        results = asyncio.run(verify(rows, summaries_only=args.summaries_only))
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps({"passed": True, "checks": len(results), "syntheticOnly": True}), flush=True)
