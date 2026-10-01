import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from time import time
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services.billing_service import BillingService
from app.services.mock_interview_repository import MockInterviewRepository, round_state
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_generation import MockGenerationUnavailable
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.realtime_speech_service import RealtimeSpeechService
from app.schemas.mock_interview import MockQuestion, MockReport
from app.services.postgres_billing_repository import PostgresBillingRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")


def mock_runtime_fixture(repositories, *, member=False):
    repo, billing, _ = repositories
    user = account(repositories, member=member)
    now = [int(time()*1000)]
    row = create(repo, user, now=now[0], free=member)
    sid = row["session_id"]
    row = repo.select_resume(user_id=user, session_id=sid, expected_version=0,
        document_id="synthetic-resume", version_id="v1", now_ms=now[0])
    reader = Mock()
    reader.read.return_value = "合成后端开发简历"
    generator = SimpleNamespace(question=AsyncMock(return_value=MockQuestion(question="如何设计幂等接口？", focus="接口设计")),
        report=AsyncMock(return_value=MockReport(summary="合成报告")))
    jobs = MockInterviewJobs(repo, reader, generator, now_ms=lambda: now[0])
    gateway = Mock()
    audio = MockInterviewAudio(gateway, now_ms=lambda: now[0])
    realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(status="live", session_mode="mock")
    device = SimpleNamespace(device_id="device", generation=1, capabilities={"mockInterviewProtocol": 1, "microphone": "granted"})
    binding = SimpleNamespace(device_id="device", binding_generation=1, status="bound", manual_code="000000")
    realtime.get_desktop_binding.return_value = binding
    realtime.repository.get_desktop_device_by_code.return_value = device
    realtime._desktop_device_fresh.return_value = True
    # Use the real interpreter: hardcoding granted hid shipped unknown heartbeats.
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    runtime = MockInterviewRuntime(repo, reader, jobs, Mock(), audio, realtime, now_ms=lambda: now[0])
    return runtime, user, sid, now, generator, billing


def test_mock_controller_start_listen_pause_submit_end_cleanup(repositories):
    async def run():
        runtime, user, sid, now, generator, billing = mock_runtime_fixture(repositories)
        messages = []
        async def send(value): messages.append(value)
        controller = await runtime.attach(user_id=user, session_id=sid, send=send)
        runtime.desktops[sid] = ("device", send)
        await runtime.command(controller, action="start", version=round_state(controller.record).version)
        await controller.generation
        state = round_state(controller.record)
        assert state.phase == "speaking" and billing.state_for_user(user_id=user).balance == 100
        await runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id)
        state = round_state(controller.record)
        old_epoch = state.capture_epoch
        assert state.phase == "listening" and runtime.audio.snapshot()["captures"] == 1
        assert billing.state_for_user(user_id=user).balance == 95
        now[0] += 2000
        await runtime.command(controller, action="pause", version=state.version)
        assert runtime.audio.snapshot()["captures"] == 0
        state = round_state(controller.record)
        await runtime.command(controller, action="resume", version=state.version)
        state = round_state(controller.record)
        assert state.capture_epoch != old_epoch and runtime.audio.snapshot()["captures"] == 1
        args = dict(action="submit", version=state.version, question_id=state.rounds[-1].question_id,
                    answer="我用业务幂等键和唯一约束避免重复写入。", submission_id="answer-1")
        generator.question.return_value = MockQuestion(question="遇到并发冲突时如何处理？", focus="并发")
        await runtime.command(controller, **args)
        await controller.generation
        await runtime.command(controller, **args)
        assert len(round_state(controller.record).rounds) == 2
        await runtime.command(controller, action="end", version=round_state(controller.record).version)
        await controller.generation
        assert round_state(controller.record).phase == "completed"
        assert runtime.audio.snapshot()["captures"] == 0
        assert controller.record["data"]["billable_ms"] == 2000
        runtime.realtime.terminate_session_for_admin.assert_called_once_with(user_id=user, session_id=sid, reason="mock-ended")
        await runtime.detach(controller)
        assert runtime.controllers == {}
        assert runtime.repository.get(user_id=user, session_id=sid)["data"]["control_token"] is None
    asyncio.run(run())


def test_controller_disconnect_cancels_provider_and_reconnect_never_autostarts_audio(repositories):
    async def run():
        runtime, user, sid, now, generator, _ = mock_runtime_fixture(repositories)
        entered, cancelled = asyncio.Event(), asyncio.Event()
        async def slow(**kwargs):
            entered.set()
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()
        generator.question.side_effect = slow
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        await runtime.command(controller, action="start", version=round_state(controller.record).version)
        await asyncio.wait_for(entered.wait(), 2)
        await runtime.detach(controller)
        assert cancelled.is_set() and runtime.controllers == {}
        restored = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        assert round_state(restored.record).phase == "generating_question"
        assert runtime.audio.snapshot()["captures"] == 0
        assert not restored.record["data"].get("generation_claim")
        assert restored.record["data"]["error"] == "generation_unavailable"
        await runtime.detach(restored)
    asyncio.run(run())


def test_controller_unknown_desktop_protocol_cannot_start_or_charge_minutes(repositories):
    async def run():
        runtime, user, sid, _, _, billing = mock_runtime_fixture(repositories)
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        runtime.realtime.repository.get_desktop_device_by_code.return_value.capabilities = {}
        with pytest.raises(DomainRequestError, match="无法确认助手"):
            await runtime.command(controller, action="start", version=round_state(controller.record).version)
        assert round_state(controller.record).phase == "preparing"
        assert billing.state_for_user(user_id=user).balance == 100
        await runtime.detach(controller)
    asyncio.run(run())


@pytest.mark.parametrize("member", [False, True])
def test_verified_repeated_provider_fault_refunds_once_and_preserves_record(repositories, member):
    async def run():
        runtime, user, sid, now, generator, billing = mock_runtime_fixture(repositories, member=member)
        initial = billing.state_for_user(user_id=user).balance
        generator.question.side_effect = MockGenerationUnavailable("安全的合成故障")
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        for action in ("start", "retry", "retry"):
            await runtime.command(controller, action=action, version=round_state(controller.record).version)
            await controller.generation
        row = controller.record
        assert round_state(row).phase == "completed" and row["refunded"] is True
        assert row["data"]["error"] == "terminal_provider_failure"
        assert row["data"]["report"]["overall_score"] is None
        assert billing.state_for_user(user_id=user).balance == initial + (0 if member else 100)
        runtime.repository.compensate_fault(user_id=user, session_id=sid, now_ms=now[0])
        assert billing.state_for_user(user_id=user).balance == initial + (0 if member else 100)
        assert runtime.repository.quote(user, now[0])["savedCount"] == 1
        if member:
            assert runtime.repository.quote(user, now[0])["dailyFreeRemaining"] == 3
        await runtime.detach(controller)
    asyncio.run(run())


def test_paid_boundary_reaper_never_renews_browser_lease(repositories):
    async def run():
        runtime, user, sid, now, _, billing = mock_runtime_fixture(repositories)
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        runtime.desktops[sid] = ("device", AsyncMock())
        await runtime.command(controller, action="start", version=round_state(controller.record).version)
        await controller.generation
        state = round_state(controller.record)
        await runtime.command(controller, action="listen", version=state.version, question_id=state.rounds[-1].question_id)
        for _ in range(11):
            now[0] += 5000
            await runtime.heartbeat(controller)
        lease = controller.record["data"]["lease_until_ms"]
        now[0] += 5000
        await runtime.reap()
        assert controller.record["data"]["billed_minutes"] == 2
        assert controller.record["data"]["lease_until_ms"] == lease
        assert billing.state_for_user(user_id=user).balance == 90
        now[0] = lease
        await runtime.reap()
        assert runtime.controllers == {} and runtime.audio.snapshot()["captures"] == 0
        assert billing.state_for_user(user_id=user).balance == 90
    asyncio.run(run())


def test_attach_send_failure_releases_control_and_memory(repositories):
    async def run():
        runtime, user, sid, _, _, _ = mock_runtime_fixture(repositories)
        with pytest.raises(RuntimeError):
            await runtime.attach(user_id=user, session_id=sid, send=AsyncMock(side_effect=RuntimeError("closed")))
        assert runtime.controllers == {}
        assert runtime.repository.get(user_id=user, session_id=sid)["data"]["control_token"] is None
    asyncio.run(run())


def test_tts_buffer_wait_does_not_accrue_minutes(repositories):
    async def run():
        runtime, user, sid, now, _, _ = mock_runtime_fixture(repositories)
        controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
        await runtime.command(controller, action="start", version=round_state(controller.record).version)
        await controller.generation
        state = round_state(controller.record)
        qid = state.rounds[-1].question_id
        controller.has_audio = True
        controller.speech_question = qid
        for action, advance in [("playback_started", 0), ("playback_waiting", 2000),
                                ("playback_started", 3000), ("playback_waiting", 1000)]:
            now[0] += advance
            await runtime.command(controller, action=action, version=state.version, question_id=qid)
        assert controller.record["data"]["billable_ms"] == 3000
        assert controller.record["data"]["billed_minutes"] == 1
        await runtime.detach(controller)
    asyncio.run(run())


def test_offline_expiry_saves_unscored_report_without_back_billing(repositories, monkeypatch):
    async def run():
        runtime, user, sid, now, _, billing = mock_runtime_fixture(repositories)
        balance = billing.state_for_user(user_id=user).balance
        now[0] += runtime.repository.settings.interview_idle_timeout_seconds*1000 + 1
        # This shared synthetic database also contains older abandoned fixtures;
        # isolate the worker's two-row scan from unrelated tests' records.
        with monkeypatch.context() as patch:
            patch.setattr(runtime.repository, "recovery_candidates", lambda **_: [runtime.repository.get(user_id=user, session_id=sid)])
            await runtime.reap()
        await asyncio.gather(*list(runtime._offline_jobs.values()))
        record = runtime.repository.get(user_id=user, session_id=sid)
        assert round_state(record).phase == "completed"
        assert record["data"]["report"]["overall_score"] is None
        assert record["data"]["billed_minutes"] == 0
        assert billing.state_for_user(user_id=user).balance == balance
        assert runtime._offline_jobs == {} and runtime.audio.snapshot()["captures"] == 0
    asyncio.run(run())


def test_offline_scan_cannot_end_a_reconnected_page(repositories):
    runtime, user, sid, now, _, _ = mock_runtime_fixture(repositories)
    now[0] += runtime.repository.settings.interview_idle_timeout_seconds*1000 + 1
    assert len(runtime.repository.recovery_candidates(now_ms=now[0], limit=100)) <= 2
    restored = runtime.repository.acquire_control(user_id=user, session_id=sid, now_ms=now[0])
    row = runtime.repository.expire_offline(user_id=user, session_id=sid, now_ms=now[0])
    assert row["data"]["control_token"] == restored["data"]["control_token"]
    assert round_state(row).phase == "preparing"


def test_repeated_complete_ten_question_sessions_release_resources(repositories):
    async def run():
        for _ in range(8):
            runtime, user, sid, now, generator, billing = mock_runtime_fixture(repositories)
            controller = await runtime.attach(user_id=user, session_id=sid, send=AsyncMock())
            runtime.desktops[sid] = ("device", AsyncMock())
            await runtime.command(controller, action="start", version=round_state(controller.record).version)
            await controller.generation
            for index in range(10):
                state = round_state(controller.record)
                qid = state.rounds[-1].question_id
                await runtime.command(controller, action="listen", version=state.version, question_id=qid)
                now[0] += 1000
                state = round_state(controller.record)
                generator.question.return_value = MockQuestion(question=f"合成场景 {index+2} 如何验证？", focus="合成验证")
                command = dict(action="submit", version=state.version, question_id=qid,
                    answer=f"合成回答 {index+1}，先列风险再做验证。", submission_id=f"answer-{index}")
                await runtime.command(controller, **command)
                await controller.generation
                await runtime.command(controller, **command)
            assert round_state(controller.record).phase == "completed"
            assert len(round_state(controller.record).rounds) == 10
            assert generator.question.await_count == 10 and generator.report.await_count == 1
            assert billing.state_for_user(user_id=user).balance == 95
            assert runtime.audio.snapshot() == {"captures": 0, "draft_characters": 0}
            await runtime.detach(controller)
            # The fake desktop sender is not a real socket; its ASGI disconnect
            # removal is separately covered by test_mock_interview_api.
            runtime.desktops.pop(sid)
            await runtime.shutdown()
            assert runtime.controllers == {} and runtime._offline_jobs == {}
            assert controller.generation.done() and controller.draft is None
    asyncio.run(run())


@pytest.fixture(scope="module")
def repositories():
    settings = Settings(_env_file=None, environment="test", database_url=DATABASE_URL)
    sessions = PostgresInterviewSessionRepository(settings)
    billing_repo = PostgresBillingRepository(settings)
    repo = MockInterviewRepository(settings)
    return repo, BillingService(settings, billing_repository=billing_repo), sessions


def account(repositories, *, member=False):
    repo, billing, _ = repositories
    user = f"synthetic-mock-{uuid4().hex}"
    assert billing.state_for_user(user_id=user).balance == 200
    if member:
        order = billing.create_checkout_order(user_id=user, product_id="pass-7", channel="alipay", idempotency_key="synthetic-pass",
            payment_url="https://synthetic.invalid", expires_at_ms=9_999_999_999_999)
        billing.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents, provider_trade_no=f"synthetic-{uuid4().hex}")
    return user


def create(repo, user, key="create", *, free=False, now=None):
    return repo.create(user_id=user, idempotency_key=key, title="合成模拟面试", target_role="后端",
        expected_billing_class="daily_pass_free" if free else "points", now_ms=now or int(time()*1000))


def finish(repo, user, session):
    def op(record, cursor):
        state = round_state(record).end()
        record["data"]["state"] = asdict(state.complete(state.operation_id))
        cursor.execute("UPDATE interview_sessions SET status='ended',continue_target='history' WHERE session_id=%s", (session,))
    return repo.change(user_id=user, session_id=session, now_ms=int(time()*1000), operation=op)


def test_atomic_idempotent_create_and_no_legacy_bill(repositories):
    repo, billing, sessions = repositories
    user = account(repositories)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: create(repo, user), range(5)))
    assert len({r["session_id"] for r in results}) == 1
    assert billing.state_for_user(user_id=user).balance == 100
    record = sessions.get_session(results[0]["session_id"])
    assert record.session_mode == "mock" and record.status == "preparing"
    assert repo.quote(user, int(time()*1000))["savedCount"] == 1
    with repo.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM billing_usage_reservations WHERE user_id=%s", (user,)).fetchone()["n"] == 0


def test_storage_cap_is_atomic_and_deletion_keeps_idempotency(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    first = create(repo, user, "first")
    def attempt(key):
        try: return create(repo, user, key)
        except DomainRequestError as exc: return exc.error_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, ["a", "b", "c", "d"]))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert results.count("mock_history_full") == 3
    assert billing.state_for_user(user_id=user).balance == 0
    finish(repo, user, first["session_id"])
    repo.delete(user_id=user, session_id=first["session_id"], now_ms=int(time()*1000))
    assert len(repo.list(user_id=user)) == 1
    with pytest.raises(DomainRequestError, match="已被删除"):
        create(repo, user, "first")
    with repo.connect() as conn:
        deleted = conn.execute("SELECT data FROM mock_interviews WHERE session_id=%s", (first["session_id"],)).fetchone()
    assert deleted["data"] == {}


def test_member_fourth_creation_paid_and_delete_does_not_restore_quota(repositories):
    repo, billing, _ = repositories
    user = account(repositories, member=True)
    now = int(time()*1000)
    for i in range(3):
        r = create(repo, user, str(i), free=True, now=now)
        finish(repo, user, r["session_id"])
        repo.delete(user_id=user, session_id=r["session_id"], now_ms=now+1)
    quote = repo.quote(user, now)
    assert quote["entryPoints"] == 100 and quote["minutePoints"] == 5
    assert quote["dailyFreeRemaining"] == 0
    with pytest.raises(DomainRequestError, match="重新确认"):
        create(repo, user, "stale-free", free=True, now=now)
    paid = create(repo, user, "fourth", now=now)
    assert paid["billing_class"] == "points" and billing.state_for_user(user_id=user).balance == 100
    assert repo.quote(user, now+86_400_000)["dailyFreeRemaining"] == 3
    assert create(repo, user, "fourth", now=now+86_400_000)["session_id"] == paid["session_id"]
    assert repo.quote(user, now+86_400_000)["dailyFreeRemaining"] == 3


def test_creation_rollback_owner_isolation_and_idempotency_parameters(repositories, monkeypatch):
    repo, billing, _ = repositories
    user = account(repositories)
    with monkeypatch.context() as patch:
        def broken(*args, **kwargs): raise RuntimeError("synthetic injected failure")
        patch.setattr(repo, "_ledger", broken)
        with pytest.raises(RuntimeError): create(repo, user)
    assert not repo.list(user_id=user)
    assert billing.state_for_user(user_id=user).balance == 200
    row = create(repo, user)
    with pytest.raises(DomainRequestError): repo.get(user_id="other-synthetic", session_id=row["session_id"])
    with pytest.raises(DomainRequestError):
        repo.create(user_id=user, idempotency_key="create", title="changed", target_role="后端", expected_billing_class="points", now_ms=int(time()*1000))


def test_fault_refund_is_once_and_rejects_client_like_fault_claim(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    record = create(repo, user)
    sid = record["session_id"]
    with pytest.raises(DomainRequestError): repo.compensate_fault(user_id=user, session_id=sid, now_ms=int(time()*1000))
    finish(repo, user, sid)
    repo.change(user_id=user, session_id=sid, now_ms=int(time()*1000), operation=lambda r, c: r["data"].update(error="terminal_provider_failure"))
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: repo.compensate_fault(user_id=user, session_id=sid, now_ms=int(time()*1000)), range(3)))
    assert billing.state_for_user(user_id=user).balance == 200


def test_last_free_slot_cannot_be_claimed_twice_or_silently_charged(repositories):
    repo, billing, _ = repositories
    user = account(repositories, member=True)
    now = int(time()*1000)
    for index in range(2):
        old = create(repo, user, f"old-{index}", free=True, now=now)
        finish(repo, user, old["session_id"])
        repo.delete(user_id=user, session_id=old["session_id"], now_ms=now)
    def attempt(key):
        try:
            return create(repo, user, key, free=True, now=now)
        except DomainRequestError as exc:
            return exc.error_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, [f"race-{i}" for i in range(4)]))
    assert sum(isinstance(item, dict) for item in results) == 1
    assert results.count("mock_price_changed") == 3
    assert billing.state_for_user(user_id=user).balance == 200
    assert repo.quote(user, now)["dailyFreeRemaining"] == 0


def test_creation_respects_existing_reserved_wallet_funds(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    # Reserve enough ordinary answer usage to leave less than the creation fee.
    for index in range(21):
        result = billing.reserve_usage(user_id=user, usage_id=f"synthetic-{user}-{index}", usage_kind="answer")
        assert result.status == "reserved"
    with pytest.raises(DomainRequestError) as caught:
        create(repo, user)
    assert caught.value.error_code == "mock_insufficient_balance"
    assert not repo.list(user_id=user)
    assert billing.state_for_user(user_id=user).balance == 200


def transition(repo, user, row, move, *, now=None):
    return repo.transition(user_id=user, session_id=row["session_id"], expected_version=round_state(row).version,
        now_ms=now or int(time()*1000), move=move)


def test_durable_rounds_single_submission_and_late_provider_fencing(repositories):
    repo, _, sessions = repositories
    user = account(repositories)
    row = transition(repo, user, create(repo, user), lambda state: state.start())
    sid = row["session_id"]
    op = round_state(row).operation_id
    now = int(time()*1000)
    def claim():
        try:
            return repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=now)
        except DomainRequestError as exc:
            return exc.error_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: claim(), range(4)))
    assert claims.count("mock_generation_in_progress") == 3
    claim_row = next(item for item in claims if isinstance(item, dict))
    row = repo.finish_generation(user_id=user, session_id=sid, operation_id=op,
        claim_id=claim_row["data"]["generation_claim"], now_ms=now+1, question="描述合成项目中的幂等设计。")
    qid = round_state(row).rounds[-1].question_id
    row = transition(repo, user, row, lambda state: state.listen(qid, now+2))
    def submit():
        return transition(repo, user, row, lambda state: state.submit(question_id=qid,
            answer="使用唯一键和事务。", submission_id="same-command"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        submitted = list(pool.map(lambda _: submit(), range(5)))
    assert len({round_state(item).operation_id for item in submitted}) == 1
    assert len(round_state(submitted[-1]).rounds) == 1
    assert round_state(repo.get(user_id=user, session_id=sid)).rounds[0].answer == "使用唯一键和事务。"
    pending = repo.claim_generation(user_id=user, session_id=sid,
        operation_id=round_state(submitted[-1]).operation_id, now_ms=now+3)
    ended = transition(repo, user, pending, lambda state: state.end(), now=now+4)
    assert sessions.get_session(sid).status == "ended"
    with pytest.raises(DomainRequestError) as caught:
        repo.finish_generation(user_id=user, session_id=sid, operation_id=round_state(pending).operation_id,
            claim_id=pending["data"]["generation_claim"], now_ms=now+5, question="不能发布的迟到题目")
    assert caught.value.error_code == "mock_stale_operation"
    assert len(round_state(ended).rounds) == 1


def test_stale_versions_expired_claims_and_one_live_session(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    first = create(repo, user, "first")
    second = create(repo, user, "second")
    live = transition(repo, user, first, lambda state: state.start())
    with pytest.raises(DomainRequestError) as caught:
        transition(repo, user, second, lambda state: state.start())
    assert caught.value.error_code == "active_interview_conflict"
    with pytest.raises(DomainRequestError) as caught:
        transition(repo, user, first, lambda state: state.end())
    assert caught.value.error_code == "mock_version_conflict"
    now = int(time()*1000)
    op = round_state(live).operation_id
    claim1 = repo.claim_generation(user_id=user, session_id=live["session_id"], operation_id=op, now_ms=now)
    deadline = claim1["data"]["generation_claim_until_ms"]
    claim2 = repo.claim_generation(user_id=user, session_id=live["session_id"], operation_id=op, now_ms=deadline)
    with pytest.raises(DomainRequestError):
        repo.finish_generation(user_id=user, session_id=live["session_id"], operation_id=op,
            claim_id=claim1["data"]["generation_claim"], now_ms=deadline+1, question="旧进程的迟到题目")
    failed = repo.finish_generation(user_id=user, session_id=live["session_id"], operation_id=op,
        claim_id=claim2["data"]["generation_claim"], now_ms=deadline+1, failed=True)
    assert failed["data"]["error"] == "generation_unavailable"
    assert not failed["data"]["generation_claim"]
    # Failure does not append questions or silently generate a score.
    assert round_state(failed).rounds == () and failed["data"]["report"] is None


def selected_live_record(repo, user):
    row = create(repo, user)
    row = repo.change(user_id=user, session_id=row["session_id"], now_ms=int(time()*1000),
        operation=lambda r, c: r["data"].update(resume_id="synthetic-resume", resume_version="v1"))
    return transition(repo, user, row, lambda state: state.start())


def test_generation_job_uses_selected_resume_and_survives_failure(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    row = selected_live_record(repo, user)
    reader = SimpleNamespace(read=Mock(return_value="合成项目正文，不持久化"))
    generator = SimpleNamespace(question=AsyncMock(side_effect=RuntimeError("sensitive synthetic error")))
    jobs = MockInterviewJobs(repo, reader, generator)
    failed = asyncio.run(jobs.run_pending(user_id=user, session_id=row["session_id"]))
    assert failed["data"]["error"] == "generation_unavailable"
    assert "sensitive" not in str(failed["data"])
    generator.question = AsyncMock(return_value=MockQuestion(question="合成问题", focus="项目"))
    result = asyncio.run(jobs.run_pending(user_id=user, session_id=row["session_id"]))
    assert round_state(result).phase == "speaking" and len(round_state(result).rounds) == 1
    reader.read.assert_called_with(user_id=user, document_id="synthetic-resume", version_id="v1")
    assert "合成项目正文" not in str(result["data"])
    assert result["data"]["error"] is None


def test_no_database_lock_during_model_wait_and_late_question_is_not_saved(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    row = selected_live_record(repo, user)
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def question(**kwargs):
            entered.set()
            await release.wait()
            return MockQuestion(question="应丢弃的迟到问题", focus="项目")
        jobs = MockInterviewJobs(repo, SimpleNamespace(read=lambda **_: "合成简历"), SimpleNamespace(question=question))
        task = asyncio.create_task(jobs.run_pending(user_id=user, session_id=row["session_id"]))
        await asyncio.wait_for(entered.wait(), 2)
        # Would time out if provider I/O held the wallet/row lock.
        await asyncio.wait_for(asyncio.to_thread(transition, repo, user, row, lambda state: state.end()), 2)
        release.set()
        result = await asyncio.wait_for(task, 2)
        assert round_state(result).phase == "generating_report"
        assert round_state(result).rounds == ()
    asyncio.run(scenario())


def test_cancelled_job_releases_claim_and_empty_report_has_no_resume_requirement(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    row = selected_live_record(repo, user)
    async def scenario():
        entered = asyncio.Event()
        async def question(**kwargs):
            entered.set()
            await asyncio.Future()
        reader = SimpleNamespace(read=Mock(return_value="合成简历"))
        generator = SimpleNamespace(question=question, report=AsyncMock(return_value=MockReport(summary="没有已确认回答，暂不评分。")))
        jobs = MockInterviewJobs(repo, reader, generator)
        task = asyncio.create_task(jobs.run_pending(user_id=user, session_id=row["session_id"]))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        record = await asyncio.to_thread(repo.get, user_id=user, session_id=row["session_id"])
        assert record["data"]["generation_claim"] is None
        ended = await asyncio.to_thread(transition, repo, user, record, lambda state: state.end())
        reader.read.reset_mock()
        report = await jobs.run_pending(user_id=user, session_id=ended["session_id"])
        reader.read.assert_not_called()
        assert round_state(report).phase == "completed"
        assert report["data"]["report"]["overall_score"] is None
    asyncio.run(scenario())


def test_ten_round_limit_survives_reload_and_deletion_preserves_charge(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    row = selected_live_record(repo, user)
    sid = row["session_id"]
    now = int(time()*1000)
    for index in range(10):
        claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=round_state(row).operation_id, now_ms=now)
        row = repo.finish_generation(user_id=user, session_id=sid, operation_id=round_state(row).operation_id,
            claim_id=claim["data"]["generation_claim"], now_ms=now+1, question=f"合成问题 {index + 1}？")
        qid = round_state(row).rounds[-1].question_id
        row = transition(repo, user, row, lambda state: state.listen(qid, now+2), now=now+2)
        row = transition(repo, user, row, lambda state: state.submit(question_id=qid,
            answer=f"已确认回答 {index + 1}", submission_id=f"answer-{index}"), now=now+3)
    reloaded_repo = MockInterviewRepository(repo.settings)
    restored = reloaded_repo.get(user_id=user, session_id=sid)
    assert len(round_state(restored).rounds) == 10
    assert round_state(restored).phase == "generating_report"
    with pytest.raises(DomainRequestError):
        transition(repo, "another-synthetic-owner", restored, lambda state: state.end())
    finish(repo, user, sid)
    with pytest.raises(DomainRequestError):
        repo.delete(user_id="another-synthetic-owner", session_id=sid, now_ms=now+4)
    repo.delete(user_id=user, session_id=sid, now_ms=now+4)
    assert billing.state_for_user(user_id=user).balance == 100
    with reloaded_repo.connect() as conn:
        tombstone = conn.execute("SELECT data FROM mock_interviews WHERE session_id=%s", (sid,)).fetchone()
    assert tombstone["data"] == {}


def test_free_creation_rollback_and_terminal_fault_restore_quota_once(repositories, monkeypatch):
    repo, billing, _ = repositories
    user = account(repositories, member=True)
    now = int(time()*1000)
    with monkeypatch.context() as patch:
        patch.setattr(repo, "_ledger", Mock(side_effect=RuntimeError("synthetic storage fault")))
        with pytest.raises(RuntimeError):
            create(repo, user, free=True, now=now)
    assert repo.quote(user, now)["dailyFreeRemaining"] == 3
    row = create(repo, user, free=True, now=now)
    assert repo.quote(user, now)["dailyFreeRemaining"] == 2
    sid = row["session_id"]
    finish(repo, user, sid)
    repo.change(user_id=user, session_id=sid, now_ms=now,
        operation=lambda r, c: r["data"].update(error="terminal_provider_failure"))
    for _ in range(3):
        repo.compensate_fault(user_id=user, session_id=sid, now_ms=now)
    assert repo.quote(user, now)["dailyFreeRemaining"] == 3
    assert billing.state_for_user(user_id=user).balance == 200


def speaking_record(repo, user, *, free=False):
    row = create(repo, user, free=free)
    row = transition(repo, user, row, lambda state: state.start())
    op = round_state(row).operation_id
    now = int(time()*1000)
    claim = repo.claim_generation(user_id=user, session_id=row["session_id"], operation_id=op, now_ms=now)
    row = repo.finish_generation(user_id=user, session_id=row["session_id"], operation_id=op,
        claim_id=claim["data"]["generation_claim"], now_ms=now, question="合成项目问题")
    return repo.acquire_control(user_id=user, session_id=row["session_id"], now_ms=now), now


def test_minute_meter_pause_resume_rounding_and_duplicate_pulses(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    row, now = speaking_record(repo, user)
    args = dict(user_id=user, session_id=row["session_id"], control_token=row["data"]["control_token"])
    repo.control_tick(**args, now_ms=now, active=True)
    for second in (10, 20):
        repo.control_tick(**args, now_ms=now+second*1000)
    row = repo.control_tick(**args, now_ms=now+25_000, active=False)
    assert row["data"]["billable_ms"] == 25_000
    # Renew an inactive connection without counting its pause.
    for second in (35, 45, 55):
        repo.control_tick(**args, now_ms=now+second*1000)
    repo.control_tick(**args, now_ms=now+60_000, active=True)
    for second in (70, 80, 90):
        repo.control_tick(**args, now_ms=now+second*1000)
    row = repo.control_tick(**args, now_ms=now+95_000, active=False)
    assert row["data"]["billable_ms"] == 60_000 and row["data"]["billed_minutes"] == 1
    assert billing.state_for_user(user_id=user).balance == 95
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: repo.control_tick(**args, now_ms=now+96_000, active=True), range(4)))
    assert billing.state_for_user(user_id=user).balance == 90


def test_minute_meter_expiry_fences_old_controller_and_does_not_bill_gap(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    row, now = speaking_record(repo, user)
    args = dict(user_id=user, session_id=row["session_id"], control_token=row["data"]["control_token"])
    repo.control_tick(**args, now_ms=now, active=True)
    before = repo.control_tick(**args, now_ms=now+5000)
    with pytest.raises(DomainRequestError):
        repo.acquire_control(user_id=user, session_id=row["session_id"], now_ms=now+6000)
    with pytest.raises(DomainRequestError):
        repo.control_tick(**args, now_ms=now+30_000)
    resumed = repo.acquire_control(user_id=user, session_id=row["session_id"], now_ms=now+300_000)
    assert resumed["data"]["billable_ms"] == before["data"]["billable_ms"] == 5000
    new_args = {**args, "control_token": resumed["data"]["control_token"]}
    active = repo.control_tick(**new_args, now_ms=now+300_000, active=True)
    repo.release_control(**args, now_ms=now+300_001)
    assert repo.get(user_id=user, session_id=row["session_id"])["data"]["control_token"] == new_args["control_token"]
    assert repo.interaction_deadline(active) == now+315_000
    assert billing.state_for_user(user_id=user).balance == 95


def test_minute_meter_membership_lock_and_exhausted_balance(repositories):
    repo, billing, _ = repositories
    member = account(repositories, member=True)
    free, now = speaking_record(repo, member, free=True)
    free_args = dict(user_id=member, session_id=free["session_id"], control_token=free["data"]["control_token"])
    for index in range(20):
        free = repo.control_tick(**free_args, now_ms=now+index*10_000, active=True)
    assert free["data"]["billed_minutes"] == 0 and billing.state_for_user(user_id=member).balance == 200
    # A fourth member session remains paid, even with an active time pass.
    finish(repo, member, free["session_id"])
    repo.delete(user_id=member, session_id=free["session_id"], now_ms=now)
    for key in ("free2", "free3"):
        r = create(repo, member, key, free=True, now=now)
        finish(repo, member, r["session_id"])
        repo.delete(user_id=member, session_id=r["session_id"], now_ms=now)
    # Use a fresh creation key because deletion deliberately keeps idempotency.
    paid = repo.create(user_id=member, idempotency_key="paid4", title="合成模拟面试", target_role="后端",
        expected_billing_class="points", now_ms=now)
    assert paid["billing_class"] == "points"
    def seed(r, c):
        state = round_state(r).start()
        r["data"]["state"] = asdict(state.publish_question(state.operation_id, "合成问题"))
        c.execute("UPDATE interview_sessions SET status='live' WHERE session_id=%s", (r["session_id"],))
    repo.change(user_id=member, session_id=paid["session_id"], now_ms=now, operation=seed)
    ctrl = repo.acquire_control(user_id=member, session_id=paid["session_id"], now_ms=now)
    args = dict(user_id=member, session_id=paid["session_id"], control_token=ctrl["data"]["control_token"])
    paid = repo.control_tick(**args, now_ms=now, active=True)
    assert paid["data"]["billed_minutes"] == 1 and billing.state_for_user(user_id=member).balance == 95
    # Existing wallet reservations prevent financing the next minute.
    for i in range(19):
        billing.reserve_usage(user_id=member, usage_id=f"held-{member}-{i}", usage_kind="answer", wallet_only=True)
    for second in (10, 20, 30, 40, 50, 60):
        paid = repo.control_tick(**args, now_ms=now+second*1000)
    assert paid["data"]["billable_ms"] == 60_000
    assert paid["data"]["clock_at_ms"] is None
    assert paid["data"]["error"] == "mock_minute_insufficient_balance"
    assert billing.state_for_user(user_id=member).balance == 95
