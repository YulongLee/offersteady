"""Global member practice: atomic quotas, UTC days, no domestic wallet access."""
from datetime import datetime, timezone

from app.services.mock_interview_repository import MockInterviewRepository, mock_error


class GlobalMockInterviewRepository(MockInterviewRepository):
    migration_name = "0052_global_mock_interviews.sql"
    interview_language = "en-US"
    lock_namespace = "global-mock-user"
    terminal_fault_summary = "Question generation repeatedly failed before any submitted answer. No score is assigned. This practice's daily allowance has been restored."

    def __init__(self, settings):
        if settings.product_edition != "global":
            raise RuntimeError("Global practice requires the Global edition")
        super().__init__(settings)

    @staticmethod
    def business_day(now_ms):
        return datetime.fromtimestamp(now_ms / 1000, timezone.utc).date()

    @staticmethod
    def _eligible(cursor, user_id, now_ms):
        cursor.execute("""SELECT e.entitlement_id FROM global_commerce_entitlements e
            JOIN global_commerce_plan_versions p ON p.offer_code=e.offer_code AND p.plan_version=e.plan_version
            WHERE e.user_id=%s AND e.status='active' AND e.starts_at_ms<=%s
              AND (e.ends_at_ms IS NULL OR e.ends_at_ms>%s) AND p.billing_mode<>'free' AND p.duration_days>=7
            LIMIT 1""", (user_id, now_ms, now_ms))
        return cursor.fetchone() is not None

    def _quote(self, cursor, user_id, now_ms):
        eligible = self._eligible(cursor, user_id, now_ms)
        restricted = self._restricted(cursor, user_id, now_ms)
        cursor.execute("SELECT count(*) AS used FROM mock_interviews WHERE owner_user_id=%s AND quota_day=%s AND NOT refunded", (user_id, self.business_day(now_ms)))
        used = int(cursor.fetchone()["used"])
        cursor.execute("SELECT count(*) AS saved FROM mock_interviews WHERE owner_user_id=%s AND deleted_at_ms IS NULL", (user_id,))
        return {"eligible": eligible, "activeTimeMember": eligible, "restricted": restricted,
                "dailyFreeRemaining": max(0, 3-used) if eligible else 0, "dailyLimit": 3,
                "entryPoints": 0, "minutePoints": 0, "billingClass": "daily_pass_free",
                "savedCount": int(cursor.fetchone()["saved"]), "savedLimit": 2,
                "quotaDay": str(self.business_day(now_ms)), "timezone": "UTC"}

    def validate_creation_quote(self, quote):
        if quote["restricted"]:
            raise mock_error("New sessions are temporarily restricted. Contact support for review.", "global_fair_use_restricted", 403)
        if not quote["eligible"]:
            raise mock_error("An active membership of 7 days or longer is required.", "global_practice_membership_required", 403)
        if quote["dailyFreeRemaining"] <= 0:
            raise mock_error("Today's 3 practice sessions have been used. Try again after 00:00 UTC.", "global_mock_daily_limit")

    def validate_start(self, cursor, user_id, now_ms):
        if self._restricted(cursor, user_id, now_ms):
            raise mock_error("New sessions are temporarily restricted. Contact support for review.", "global_fair_use_restricted", 403)
        if not self._eligible(cursor, user_id, now_ms):
            raise mock_error("An active membership of 7 days or longer is required to start.", "global_practice_membership_required", 403)

    @staticmethod
    def _restricted(cursor, user_id, now_ms):
        cursor.execute("""SELECT status, restrict_new_sessions FROM global_commerce_fair_use_decisions
            WHERE user_id=%s AND status IN ('review','restricted') AND effective_at_ms<=%s
              AND (expires_at_ms IS NULL OR expires_at_ms>%s) ORDER BY effective_at_ms DESC LIMIT 1""",
            (user_id, now_ms, now_ms))
        decision = cursor.fetchone()
        return bool(decision and decision["status"] == "restricted" and decision["restrict_new_sessions"])

    @staticmethod
    def _ledger(*args, **kwargs):
        # The durable mock row is the quota record. Never use the CN ledger.
        return None

    @staticmethod
    def _available(*args, **kwargs):
        raise RuntimeError("Global practice must never access a points wallet")
