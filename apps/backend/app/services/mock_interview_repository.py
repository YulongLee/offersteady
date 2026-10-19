"""Durable owner-scoped mock records and atomic wallet/quota operations.

Shares the existing billing-user transaction lock; no provider calls belong here.
Deleted history keeps only financial/idempotency metadata, never Q&A or resumes.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import REPO_ROOT, Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionConfigSnapshot, SessionMaterialBinding, SessionUsageTotals
from app.services.mock_interview_rounds import MockRound, MockRoundState
from app.services.postgres_migrations import apply_sql_migrations


def mock_error(message: str, code: str, status: int = 409):
    return DomainRequestError("mock-interview", "command", message, status, code)


def round_state(record: dict) -> MockRoundState:
    data = dict(record["data"]["state"])
    data["rounds"] = tuple(MockRound(**item) for item in data.get("rounds", []))
    return MockRoundState(**data)


class MockInterviewRepository:
    control_lease_ms = 15_000
    migration_name = "0051_mock_interviews.sql"
    interview_language = "zh-CN"
    lock_namespace = "billing-user"
    terminal_fault_summary = "出题服务连续失败，本场未完成作答，不进行评分。费用或免费次数已退还。"
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.database_url:
            raise RuntimeError("Mock interviews require durable PostgreSQL storage")
        with self.connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, [REPO_ROOT / "apps/backend/migrations/versions" / self.migration_name])

    def connect(self):
        return psycopg.connect(self.settings.database_url, row_factory=dict_row,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name="offersteady-mock-interview")

    @contextmanager
    def transaction(self, user_id: str):
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"{self.lock_namespace}:{user_id}",))
            yield cursor

    @staticmethod
    def business_day(now_ms: int):
        return datetime.fromtimestamp(now_ms / 1000, ZoneInfo("Asia/Shanghai")).date()

    def _quote(self, cursor, user_id: str, now_ms: int) -> dict:
        cursor.execute("SELECT 1 FROM billing_time_pass_entitlements WHERE user_id=%s AND starts_at_ms<=%s AND ends_at_ms>%s LIMIT 1", (user_id, now_ms, now_ms))
        member = cursor.fetchone() is not None
        cursor.execute("SELECT to_regclass('admin_time_entitlements') AS name")
        if cursor.fetchone()["name"] is not None and not member:
            cursor.execute("SELECT 1 FROM admin_time_entitlements WHERE user_id=%s AND starts_at_ms<=%s AND ends_at_ms>%s LIMIT 1", (user_id, now_ms, now_ms))
            member = cursor.fetchone() is not None
        cursor.execute("SELECT count(*) AS used FROM mock_interviews WHERE owner_user_id=%s AND quota_day=%s AND billing_class='daily_pass_free' AND NOT refunded", (user_id, self.business_day(now_ms)))
        used = int(cursor.fetchone()["used"])
        cursor.execute("SELECT count(*) AS saved FROM mock_interviews WHERE owner_user_id=%s AND deleted_at_ms IS NULL", (user_id,))
        saved = int(cursor.fetchone()["saved"])
        free = member and used < 3
        return {"activeTimeMember": member, "dailyFreeRemaining": max(0, 3-used) if member else 0,
                "entryPoints": 0 if free else 100, "minutePoints": 0 if free else 5,
                "billingClass": "daily_pass_free" if free else "points", "savedCount": saved,
                "savedLimit": 2, "quotaDay": str(self.business_day(now_ms)), "timezone": "Asia/Shanghai"}

    def quote(self, user_id: str, now_ms: int) -> dict:
        with self.transaction(user_id) as cursor:
            return self._quote(cursor, user_id, now_ms)

    def validate_creation_quote(self, quote: dict) -> None:
        """Edition-specific admission before any record or fee is written."""

    def validate_start(self, cursor, user_id: str, now_ms: int) -> None:
        """Existing CN sessions keep their creation-time billing contract."""

    @staticmethod
    def _available(cursor, user_id: str) -> int:
        cursor.execute("""SELECT COALESCE((SELECT SUM(points) FROM points_redemption_ledger WHERE user_id=%s),0)
            - COALESCE((SELECT SUM(points_reserved) FROM billing_usage_reservations WHERE user_id=%s AND status='reserved'),0)
            - COALESCE((SELECT SUM(points_reserved) FROM billing_index_reservations WHERE user_id=%s AND status='reserved'),0) AS available""", (user_id, user_id, user_id))
        return int(cursor.fetchone()["available"])

    @staticmethod
    def _ledger(cursor, *, user_id: str, session_id: str, kind: str, points: int, reference: str, now_ms: int):
        cursor.execute("""INSERT INTO points_redemption_ledger
            (ledger_entry_id,user_id,kind,points,created_at_ms,reference_id,description)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (reference_id) DO NOTHING""",
            (f"ledger-mock-{uuid4().hex}", user_id, kind, points, now_ms, reference,
             {"mock_interview_entry_settlement": "模拟面试创建", "mock_interview_minute_settlement": "模拟面试分钟费",
              "mock_interview_refund": "模拟面试故障退还", "pass_usage": "模拟面试每日会员免费权益"}[kind]))

    def create(self, *, user_id: str, idempotency_key: str, title: str, target_role: str,
               expected_billing_class: str, now_ms: int) -> dict:
        if not (1 <= len(idempotency_key) <= 128 and 1 <= len(title.strip()) <= 120 and len(target_role) <= 120):
            raise mock_error("创建参数无效。", "mock_invalid_creation", 422)
        with self.transaction(user_id) as cursor:
            cursor.execute("SELECT * FROM mock_interviews WHERE owner_user_id=%s AND idempotency_key=%s", (user_id, idempotency_key))
            existing = cursor.fetchone()
            if existing:
                if existing["deleted_at_ms"] is not None:
                    raise mock_error("该创建请求对应的记录已被删除，请重新创建。", "mock_creation_deleted")
                if (existing["data"]["title"], existing["data"]["target_role"]) != (title.strip(), target_role.strip()):
                    raise mock_error("创建标识已用于另一组参数。", "mock_idempotency_conflict")
                return existing
            quote = self._quote(cursor, user_id, now_ms)
            self.validate_creation_quote(quote)
            if quote["savedCount"] >= 2:
                raise mock_error("最多保留两条模拟面试记录，请先手动删除旧记录。", "mock_history_full")
            if quote["billingClass"] != expected_billing_class:
                raise mock_error("会员免费次数或本场价格已变化，请重新确认。", "mock_price_changed")
            if quote["entryPoints"] and self._available(cursor, user_id) < quote["entryPoints"]:
                raise mock_error("积分不足，创建模拟面试需要 100 积分。", "mock_insufficient_balance", 402)
            session_id = f"mock-{uuid4().hex}"
            material = SessionMaterialBinding(session_id, user_id, 0, None, None)
            config = SessionConfigSnapshot("mock-v1", "mock-v1", "selected-resume", "mock-v1", now_ms)
            cursor.execute("""INSERT INTO interview_sessions
                (session_id,owner_user_id,title,session_mode,interview_audio_mode,interview_language,status,continue_target,
                 material_binding_json,config_snapshot_json,usage_totals_json,integration_references_json,
                 created_at_ms,updated_at_ms,last_activity_at_ms)
                VALUES (%s,%s,%s,'mock','mobile',%s,'preparing','preparing',%s,%s,%s,'[]',%s,%s,%s)""",
                (session_id, user_id, title.strip(), self.interview_language, Jsonb(asdict(material)), Jsonb(asdict(config)),
                 Jsonb(asdict(SessionUsageTotals())), now_ms, now_ms, now_ms))
            data = {"title": title.strip(), "target_role": target_role.strip(), "state": asdict(MockRoundState()),
                    "resume_id": None, "resume_version": None, "report": None, "error": None,
                    "billable_ms": 0, "billed_minutes": 0, "clock_at_ms": None, "lease_until_ms": 0}
            cursor.execute("""INSERT INTO mock_interviews
                (session_id,owner_user_id,idempotency_key,billing_class,quota_day,created_at_ms,updated_at_ms,data)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (session_id, user_id, idempotency_key, quote["billingClass"], self.business_day(now_ms), now_ms, now_ms, Jsonb(data)))
            record = cursor.fetchone()
            self._ledger(cursor, user_id=user_id, session_id=session_id,
                kind="pass_usage" if quote["entryPoints"] == 0 else "mock_interview_entry_settlement",
                points=-quote["entryPoints"], reference=f"mock:{session_id}:entry", now_ms=now_ms)
            return record

    def get(self, *, user_id: str, session_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM mock_interviews WHERE owner_user_id=%s AND session_id=%s AND deleted_at_ms IS NULL", (user_id, session_id)).fetchone()
        if row is None:
            raise mock_error("模拟面试不存在或无权访问。", "mock_not_found", 404)
        return row

    def list(self, *, user_id: str) -> list[dict]:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM mock_interviews WHERE owner_user_id=%s AND deleted_at_ms IS NULL ORDER BY created_at_ms DESC", (user_id,)).fetchall()

    def change(self, *, user_id: str, session_id: str, now_ms: int, operation: Callable) -> dict:
        with self.transaction(user_id) as cursor:
            cursor.execute("SELECT * FROM mock_interviews WHERE owner_user_id=%s AND session_id=%s AND deleted_at_ms IS NULL FOR UPDATE", (user_id, session_id))
            record = cursor.fetchone()
            if record is None:
                raise mock_error("模拟面试不存在或无权访问。", "mock_not_found", 404)
            operation(record, cursor)
            cursor.execute("""UPDATE mock_interviews SET data=%s,refunded=%s,deleted_at_ms=%s,
                updated_at_ms=%s,revision=revision+1 WHERE session_id=%s RETURNING *""",
                (Jsonb(record["data"]), record["refunded"], record["deleted_at_ms"], now_ms, session_id))
            return cursor.fetchone()

    def delete(self, *, user_id: str, session_id: str, now_ms: int) -> dict:
        def operation(record, cursor):
            if round_state(record).phase != "completed":
                raise mock_error("请先结束面试再删除记录。", "mock_not_completed")
            record["data"] = {}
            record["deleted_at_ms"] = now_ms
            cursor.execute("DELETE FROM interview_session_context_entries WHERE session_id=%s", (session_id,))
            cursor.execute("UPDATE interview_sessions SET deleted_at_ms=%s,title='',material_binding_json='{}',integration_references_json='[]' WHERE session_id=%s", (now_ms, session_id))
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def transition(self, *, user_id: str, session_id: str, expected_version: int,
                   now_ms: int, move: Callable[[MockRoundState], MockRoundState]) -> dict:
        """Internal CAS primitive, not a generic client-selectable state command.

        Caller owns resume/device validation and the approved minute meter. This
        primitive alone must not be wired to a public start/listen endpoint.
        """
        def operation(record, cursor):
            previous = round_state(record)
            following = move(previous)
            # Idempotent answer retries can have an old version after advancement.
            if following == previous:
                return
            if previous.version != expected_version:
                raise mock_error("面试进度已变化，请恢复最新进度。", "mock_version_conflict")
            self._meter(record, cursor, now_ms=now_ms, active=False)
            cursor.execute("SELECT status FROM interview_sessions WHERE session_id=%s FOR UPDATE", (session_id,))
            base = cursor.fetchone()
            if following.phase not in ("generating_report", "completed"):
                if base is None or base["status"] == "ended":
                    raise mock_error("本场面试已结束。", "mock_session_ended")
            if previous.phase == "preparing" and following.phase == "generating_question":
                self.validate_start(cursor, user_id, now_ms)
                # The existing unique partial index serializes concurrent starts
                # with ordinary interviews as well as other mock interviews.
                cursor.execute("""UPDATE interview_sessions SET status='live',continue_target='live',
                    started_at_ms=%s,updated_at_ms=%s,last_activity_at_ms=%s WHERE session_id=%s""",
                    (now_ms, now_ms, now_ms, session_id))
            if following.phase in ("generating_report", "completed"):
                cursor.execute("""UPDATE interview_sessions SET status='ended',continue_target='history',
                    ended_at_ms=COALESCE(ended_at_ms,%s),updated_at_ms=%s WHERE session_id=%s""",
                    (now_ms, now_ms, session_id))
            record["data"]["state"] = asdict(following)
            if following.operation_id != previous.operation_id:
                record["data"].update(generation_claim=None, generation_claim_until_ms=0, error=None)
        try:
            return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)
        except psycopg.errors.UniqueViolation as exc:
            if exc.diag.constraint_name != "uq_interview_sessions_one_live_per_user":
                raise
            raise mock_error("当前账号已有进行中的面试，请先结束上一场。", "active_interview_conflict") from None

    def select_resume(self, *, user_id: str, session_id: str, expected_version: int,
                      document_id: str, version_id: str, now_ms: int) -> dict:
        # Caller must validate the parsed artifact before entering this transaction.
        def operation(record, cursor):
            state = round_state(record)
            if state.phase != "preparing" or state.version != expected_version:
                raise mock_error("仅可在准备阶段选择简历，请恢复最新进度。", "mock_version_conflict")
            record["data"].update(resume_id=document_id, resume_version=version_id,
                                state=asdict(state._move()))
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def recovery_candidates(self, *, now_ms: int, limit: int = 2) -> list[dict]:
        cutoff = now_ms - self.settings.interview_idle_timeout_seconds * 1000
        with self.connect() as connection:
            return connection.execute("""SELECT m.* FROM mock_interviews m
                JOIN interview_sessions s USING (session_id)
                WHERE m.deleted_at_ms IS NULL AND m.data->'state'->>'phase' <> 'completed'
                AND COALESCE((m.data->>'lease_until_ms')::bigint,0) <= %s
                AND m.updated_at_ms <= %s ORDER BY m.updated_at_ms LIMIT %s""",
                (now_ms, cutoff, min(max(limit, 1), 2))).fetchall()

    def expire_offline(self, *, user_id: str, session_id: str, now_ms: int) -> dict:
        def operation(record, cursor):
            state = round_state(record)
            # Recheck after taking the same lock as reconnect/start. A scan must
            # never end a page that reconnected between SELECT and transaction.
            if (state.phase == "completed" or record["data"].get("lease_until_ms", 0) > now_ms
                    or record["updated_at_ms"] > now_ms-self.settings.interview_idle_timeout_seconds*1000):
                return
            self._meter(record, cursor, now_ms=now_ms, active=False)
            following = state.end()
            record["data"].update(state=asdict(following), control_token=None, lease_until_ms=0)
            if following.operation_id != state.operation_id:
                record["data"].update(generation_claim=None, generation_claim_until_ms=0)
            cursor.execute("""UPDATE interview_sessions SET status='ended',continue_target='history',
                ended_at_ms=COALESCE(ended_at_ms,%s),updated_at_ms=%s WHERE session_id=%s""", (now_ms, now_ms, session_id))
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def acquire_control(self, *, user_id: str, session_id: str, now_ms: int) -> dict:
        def operation(record, cursor):
            if round_state(record).phase == "completed":
                raise mock_error("本场面试已结束。", "mock_session_ended")
            data = record["data"]
            if data.get("control_token") and data.get("lease_until_ms", 0) > now_ms:
                raise mock_error("本场已在另一页面连接，请关闭原页面后重试。", "mock_control_in_use")
            # An expired connection does not accrue its unconfirmed tail/gap.
            data.update(control_token=uuid4().hex, lease_until_ms=now_ms+self.control_lease_ms, clock_at_ms=None)
            if round_state(record).phase in ("generating_question", "generating_report"):
                # A process death cannot leave the UI spinning without a retry
                # action. Explicit retry changes the operation fence, so a late
                # result from the previous worker cannot overwrite new output.
                data["error"] = "generation_unavailable"
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def control_tick(self, *, user_id: str, session_id: str, control_token: str,
                     now_ms: int, active: bool | None = None, renew_lease: bool = True) -> dict:
        def operation(record, cursor):
            data = record["data"]
            if data.get("control_token") != control_token or data.get("lease_until_ms", 0) <= now_ms:
                raise mock_error("连接已过期，请重新连接；断线时间不计费。", "mock_control_expired")
            wanted = data.get("clock_at_ms") is not None if active is None else active
            if wanted:
                if round_state(record).phase not in ("speaking", "listening"):
                    raise mock_error("当前不是交互阶段。", "mock_not_interacting")
                cursor.execute("SELECT status FROM interview_sessions WHERE session_id=%s FOR UPDATE", (session_id,))
                base = cursor.fetchone()
                if base is None or base["status"] != "live":
                    wanted = False
            self._meter(record, cursor, now_ms=now_ms, active=wanted)
            if renew_lease:
                data["lease_until_ms"] = now_ms + self.control_lease_ms
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def release_control(self, *, user_id: str, session_id: str, control_token: str, now_ms: int) -> dict:
        def operation(record, cursor):
            if record["data"].get("control_token") != control_token:
                return  # A late disconnect must never close the new controller.
            self._meter(record, cursor, now_ms=now_ms, active=False)
            record["data"].update(control_token=None, lease_until_ms=0)
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def _meter(self, record, cursor, *, now_ms: int, active: bool) -> None:
        data = record["data"]
        total = int(data.get("billable_ms", 0))
        purchased = int(data.get("billed_minutes", 0))
        free = record["billing_class"] == "daily_pass_free"
        previous = data.get("clock_at_ms")
        if previous is not None and now_ms < previous:
            raise mock_error("计费时钟异常，请重试。", "mock_clock_conflict")
        if previous is not None and data.get("lease_until_ms", 0) > now_ms:
            elapsed = now_ms - previous
            # Eligibility expires at the paid boundary; never accumulate debt
            # while awaiting the next pulse or a delayed request.
            if not free:
                elapsed = min(elapsed, max(0, purchased * 60_000 - total))
            total += elapsed
        if active and not free and total >= purchased * 60_000:
            if self._available(cursor, record["owner_user_id"]) < 5:
                active = False
                data["error"] = "mock_minute_insufficient_balance"
            else:
                purchased += 1
                self._ledger(cursor, user_id=record["owner_user_id"], session_id=record["session_id"],
                    kind="mock_interview_minute_settlement", points=-5,
                    reference=f"mock:{record['session_id']}:minute:{purchased}", now_ms=now_ms)
                if data.get("error") == "mock_minute_insufficient_balance":
                    data["error"] = None
        data.update(billable_ms=total, billed_minutes=purchased, clock_at_ms=now_ms if active else None)

    @staticmethod
    def interaction_deadline(record: dict) -> int:
        data = record["data"]
        clock = data.get("clock_at_ms")
        if clock is None:
            return 0
        deadline = data.get("lease_until_ms", 0)
        if record["billing_class"] == "points":
            deadline = min(deadline, clock + max(0, data["billed_minutes"] * 60_000 - data["billable_ms"]))
        return deadline

    def claim_generation(self, *, user_id: str, session_id: str, operation_id: str,
                         now_ms: int) -> dict:
        """Durable bounded lease: retries/workers cannot launch the same job twice."""
        def operation(record, cursor):
            state = round_state(record)
            if state.phase not in ("generating_question", "generating_report") or state.operation_id != operation_id:
                raise mock_error("生成任务已过期。", "mock_stale_operation")
            if record["data"].get("generation_claim_until_ms", 0) > now_ms:
                raise mock_error("正在生成，请等待当前任务完成。", "mock_generation_in_progress")
            record["data"].update(generation_claim=uuid4().hex,
                generation_claim_until_ms=now_ms + int(self.settings.mock_interview_provider_timeout_seconds * 1000) + 15_000,
                error=None)
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def finish_generation(self, *, user_id: str, session_id: str, operation_id: str,
                          claim_id: str, now_ms: int, question: str | None = None,
                          report: dict | None = None, failed: bool = False,
                          provider_fault: bool = False) -> dict:
        def operation(record, cursor):
            state = round_state(record)
            if (state.operation_id != operation_id or record["data"].get("generation_claim") != claim_id
                    or record["data"].get("generation_claim_until_ms", 0) <= now_ms):
                raise mock_error("生成任务已过期，结果已丢弃。", "mock_stale_operation")
            if state.phase == "generating_question":
                cursor.execute("SELECT status FROM interview_sessions WHERE session_id=%s FOR UPDATE", (session_id,))
                base = cursor.fetchone()
                if base is None or base["status"] != "live":
                    raise mock_error("本场面试已结束，题目已丢弃。", "mock_session_ended")
            if failed:
                record["data"]["error"] = "generation_unavailable"
                if provider_fault:
                    failures = int(record["data"].get("provider_failures", 0)) + 1
                    record["data"]["provider_failures"] = failures
                    if failures >= 3 and state.phase == "generating_question" and not any(r.answer for r in state.rounds):
                        ending = state.end()
                        record["data"]["state"] = asdict(ending.complete(ending.operation_id))
                        record["data"]["report"] = {"summary": self.terminal_fault_summary,
                            "dimensions": None, "overall_score": None, "feedback": [], "practice_priorities": []}
                        record["data"]["error"] = "terminal_provider_failure"
                        self._meter(record, cursor, now_ms=now_ms, active=False)
                        cursor.execute("UPDATE interview_sessions SET status='ended',continue_target='history',ended_at_ms=%s WHERE session_id=%s", (now_ms, session_id))
                        if record["billing_class"] == "points" and not record["refunded"]:
                            self._ledger(cursor, user_id=user_id, session_id=session_id,
                                kind="mock_interview_refund", points=100+5*record["data"]["billed_minutes"],
                                reference=f"mock:{session_id}:refund", now_ms=now_ms)
                        record["refunded"] = True
            elif state.phase == "generating_question" and question is not None and report is None:
                record["data"]["state"] = asdict(state.publish_question(operation_id, question))
                record["data"]["provider_failures"] = 0
            elif state.phase == "generating_report" and report is not None and question is None:
                record["data"]["state"] = asdict(state.complete(operation_id))
                record["data"]["report"] = report
            else:
                raise mock_error("生成结果与当前阶段不符。", "mock_invalid_generation")
            record["data"].update(generation_claim=None, generation_claim_until_ms=0)
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)

    def compensate_fault(self, *, user_id: str, session_id: str, now_ms: int) -> dict:
        # Only a trusted service fault path may call this; no public refund flag.
        def operation(record, cursor):
            state = round_state(record)
            if record["refunded"] or any(r.answer for r in state.rounds):
                return
            if record["data"].get("error") != "terminal_provider_failure" or state.phase != "completed":
                raise mock_error("当前场次不符合故障退款条件。", "mock_refund_unavailable")
            if record["billing_class"] == "points":
                refund = 100 + record["data"]["billed_minutes"] * 5
                self._ledger(cursor, user_id=user_id, session_id=session_id, kind="mock_interview_refund",
                    points=refund, reference=f"mock:{session_id}:refund", now_ms=now_ms)
            record["refunded"] = True
        return self.change(user_id=user_id, session_id=session_id, now_ms=now_ms, operation=operation)
