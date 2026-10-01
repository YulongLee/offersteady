import pytest

from app.core.errors import DomainRequestError
from app.services.mock_interview_rounds import MockRoundState


def listening():
    state = MockRoundState().start()
    state = state.publish_question(state.operation_id, "介绍合成项目。")
    return state.listen(state.rounds[-1].question_id, 100)


def test_ten_total_questions_manual_completion_and_idempotency():
    state = MockRoundState().start()
    for index in range(10):
        state = state.publish_question(state.operation_id, f"合成问题 {index}？")
        qid = state.rounds[-1].question_id
        assert state.phase == "speaking"
        state = state.listen(qid, index * 1000)
        assert state.phase == "listening"  # Silence has no transition.
        state = state.submit(question_id=qid, answer="合成回答", submission_id=str(index))
        version = state.version
        assert state.submit(question_id=qid, answer="合成回答", submission_id=str(index)) == state
        assert state.version == version
    assert state.phase == "generating_report"
    with pytest.raises(DomainRequestError):
        state.publish_question(state.operation_id, "第十一题？")
    state = state.complete(state.operation_id)
    assert state.phase == "completed" and len(state.rounds) == 10


def test_stale_round_and_mutated_idempotent_request_fail():
    state = listening()
    qid = state.rounds[-1].question_id
    with pytest.raises(DomainRequestError):
        state.submit(question_id=qid, answer=" ", submission_id="submit")
    state = state.submit(question_id=qid, answer="原回答", submission_id="submit")
    with pytest.raises(DomainRequestError):
        state.submit(question_id=qid, answer="不同回答", submission_id="submit")
    with pytest.raises(DomainRequestError):
        state.submit(question_id=qid, answer="原回答", submission_id="other-tab")


def test_capture_replay_and_late_results_are_fenced():
    state = listening()
    qid, epoch = state.rounds[-1].question_id, state.capture_epoch
    assert state.accepts_capture(question_id=qid, epoch=epoch, started_at_ms=100)
    assert not state.accepts_capture(question_id=qid, epoch=epoch, started_at_ms=99)
    state = state.replay(qid)
    assert not state.accepts_capture(question_id=qid, epoch=epoch, started_at_ms=101)
    state = state.listen(qid, 200)
    assert not state.accepts_capture(question_id=qid, epoch=epoch, started_at_ms=201)
    state = state.end()
    op = state.operation_id
    state = state.retry_generation()
    with pytest.raises(DomainRequestError):
        state.complete(op)
    assert state.end() == state


def test_early_end_prevents_late_question_and_repeated_question():
    initial = MockRoundState().start()
    state = initial.end()
    with pytest.raises(DomainRequestError):
        state.publish_question(initial.operation_id, "迟到题目")
    state = listening()
    state = state.submit(question_id=state.rounds[-1].question_id, answer="合成回答", submission_id="answer")
    with pytest.raises(DomainRequestError):
        state.publish_question(state.operation_id, "介绍合成项目。")
