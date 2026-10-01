"""Pure, immutable transitions; persistence must compare-and-swap version.

These operations do not start legacy answer jobs, capture audio or deduct points.
An operation token fences provider results after retries, end and cancellation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal
from uuid import uuid4

from app.core.errors import DomainRequestError


Phase = Literal["preparing", "generating_question", "speaking", "listening", "paused", "generating_report", "completed"]


def conflict(message: str, code: str = "mock_state_conflict") -> DomainRequestError:
    return DomainRequestError("mock-interview", "transition", message, 409, code)


@dataclass(frozen=True)
class MockRound:
    question_id: str
    question: str
    answer: str | None = None
    submission_id: str | None = None


@dataclass(frozen=True)
class MockRoundState:
    phase: Phase = "preparing"
    version: int = 0
    rounds: tuple[MockRound, ...] = ()
    operation_id: str | None = None
    capture_epoch: str | None = None
    capture_opened_at_ms: int | None = None
    paused_from: str | None = None

    def _move(self, **values) -> MockRoundState:
        return replace(self, version=self.version + 1, **values)

    def start(self) -> MockRoundState:
        if self.phase != "preparing":
            raise conflict("面试已经开始，请恢复当前进度。")
        return self._move(phase="generating_question", operation_id=uuid4().hex)

    def publish_question(self, operation_id: str, text: str) -> MockRoundState:
        if self.phase != "generating_question" or operation_id != self.operation_id:
            raise conflict("过期的出题结果已丢弃。", "mock_stale_operation")
        text = text.strip()
        if not text or len(text) > 800:
            raise conflict("题目格式异常，请重试。", "mock_invalid_question")
        if len(self.rounds) >= 10:
            raise conflict("本场已达到十题上限。", "mock_question_limit")
        if any(r.question == text for r in self.rounds):
            raise conflict("生成了重复题目，请重试。", "mock_repeated_question")
        return self._move(phase="speaking", operation_id=None,
                          rounds=(*self.rounds, MockRound(uuid4().hex, text)))

    def listen(self, question_id: str, now_ms: int) -> MockRoundState:
        if self.phase != "speaking" or not self.rounds or self.rounds[-1].question_id != question_id:
            raise conflict("当前题目已变化，请刷新进度。")
        return self._move(phase="listening", capture_epoch=uuid4().hex, capture_opened_at_ms=now_ms)

    def accepts_capture(self, *, question_id: str, epoch: str, started_at_ms: int) -> bool:
        return bool(self.phase == "listening" and self.rounds and self.rounds[-1].question_id == question_id
                    and self.capture_epoch == epoch and self.capture_opened_at_ms is not None
                    and started_at_ms >= self.capture_opened_at_ms)

    def replay(self, question_id: str) -> MockRoundState:
        if self.phase != "listening" or self.rounds[-1].question_id != question_id:
            raise conflict("当前无法重播该题。")
        return self._move(phase="speaking", capture_epoch=None, capture_opened_at_ms=None)

    def pause(self) -> MockRoundState:
        if self.phase == "paused":
            return self
        if self.phase not in ("speaking", "listening"):
            raise conflict("当前阶段不需要暂停。")
        return self._move(phase="paused", paused_from=self.phase,
                          capture_epoch=None, capture_opened_at_ms=None)

    def resume(self, now_ms: int) -> MockRoundState:
        if self.phase != "paused" or self.paused_from not in ("speaking", "listening"):
            raise conflict("当前无需恢复。")
        listening = self.paused_from == "listening"
        return self._move(phase=self.paused_from, paused_from=None,
                          capture_epoch=uuid4().hex if listening else None,
                          capture_opened_at_ms=now_ms if listening else None)

    def submit(self, *, question_id: str, answer: str, submission_id: str) -> MockRoundState:
        answer = answer.strip()
        if not submission_id or len(submission_id) > 128 or not answer or len(answer) > 8_000:
            raise conflict("请确认非空回答，且回答不超过 8000 字。", "mock_invalid_answer")
        existing = next((r for r in self.rounds if r.submission_id == submission_id), None)
        if existing:
            if existing.question_id != question_id or existing.answer != answer:
                raise conflict("重复提交标识与原回答不一致。", "mock_idempotency_conflict")
            return self
        if self.phase != "listening" or self.rounds[-1].question_id != question_id:
            raise conflict("该题已提交或不是当前题目。", "mock_stale_round")
        answered = replace(self.rounds[-1], answer=answer, submission_id=submission_id)
        return self._move(rounds=(*self.rounds[:-1], answered),
                          phase="generating_report" if len(self.rounds) == 10 else "generating_question",
                          operation_id=uuid4().hex, capture_epoch=None, capture_opened_at_ms=None)

    def end(self) -> MockRoundState:
        if self.phase in ("generating_report", "completed"):
            return self
        return self._move(phase="generating_report", operation_id=uuid4().hex,
                          capture_epoch=None, capture_opened_at_ms=None)

    def retry_generation(self) -> MockRoundState:
        if self.phase not in ("generating_question", "generating_report"):
            raise conflict("当前阶段无需重试生成。")
        return self._move(operation_id=uuid4().hex)

    def complete(self, operation_id: str) -> MockRoundState:
        if self.phase != "generating_report" or self.operation_id != operation_id:
            raise conflict("过期的报告结果已丢弃。", "mock_stale_operation")
        return self._move(phase="completed", operation_id=None, capture_epoch=None, capture_opened_at_ms=None)
