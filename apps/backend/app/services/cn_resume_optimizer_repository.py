"""CN optimizer transactions share the existing immutable wallet and account lock."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import json
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import REPO_ROOT, Settings
from app.core.errors import DomainRequestError
from app.services.cn_resume_optimizer_diagnostics import failure_diagnostic, normalize_failure_diagnostic
from app.services.postgres_migrations import apply_sql_migrations


DAILY_FREE_LIMIT = 3


ERRORS = {
    "not_found": (404, "优化任务不存在或无权访问。"),
    "source_markup_unsupported": (422, "解析后的简历或岗位资料包含不支持的格式，请使用不含 HTML 的纯文本或 Markdown 后重试。"),
    "source_unavailable": (409, "所选简历或岗位资料版本已失效，请选择处理完成的资料后重试。"),
    "busy": (429, "简历优化任务繁忙，请完成当前任务或稍后重试。"),
    "quote_changed": (409, "免费次数、会员状态或本次报价已变化，请刷新并重新确认。"),
    "insufficient_balance": (402, "可用积分不足，本次简历优化需要 100 积分。"),
    "points_confirmation_required": (422, "请明确确认本次使用 100 积分后再开始优化。"),
    "idempotency_conflict": (409, "该请求标识已用于其他内容，请重新发起优化。"),
    "revision_conflict": (409, "优化稿已发生变化，请重新载入后再保存、下载或另存。"),
    "not_completed": (409, "请先完成优化，再编辑、下载或另存简历。"),
    "invalid_draft": (422, "请使用不超过 60,000 字符的非空纯文本或 Markdown，不支持 HTML 或控制字符。"),
    "disabled": (404, "当前服务未开放简历优化。"),
    "provider_unconfigured": (503, "简历优化服务暂时不可用，请稍后重试。"),
}


def optimizer_error(code: str):
    status, message = ERRORS[code]
    return DomainRequestError("resume-optimizer", "request", message, status,
                              error_code="resume_optimizer_" + code)


def quota_day(now_ms: int) -> str:
    return str(datetime.fromtimestamp(now_ms / 1000, ZoneInfo("Asia/Shanghai")).date())


def reset_at(now_ms: int) -> int:
    date = datetime.fromtimestamp(now_ms / 1000, ZoneInfo("Asia/Shanghai")).date() + timedelta(days=1)
    return int(datetime.combine(date, datetime.min.time(), tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000)


def input_fingerprint(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class CNResumeOptimizerRepository:
    lease_ms = 120_000
    queue_lifetime_ms = 15 * 60_000
    capacity = 8

    def __init__(self, settings: Settings, *, initialize=True):
        if settings.product_edition != "cn" or not settings.database_url:
            raise RuntimeError("CN Resume Optimizer requires durable CN PostgreSQL storage")
        self.settings = settings
        if initialize:
            with self.connect() as connection, connection.cursor() as cursor:
                apply_sql_migrations(cursor, [REPO_ROOT / "apps/backend/migrations/versions/0054_cn_resume_optimizer.sql"])

    def connect(self):
        return psycopg.connect(self.settings.database_url, row_factory=dict_row,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name="offersteady-cn-resume-optimizer")

    @contextmanager
    def transaction(self, user_id=None, *, global_lock=True, wallet=True):
        with self.connect() as connection, connection.cursor() as cursor:
            if global_lock:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('cn-resume-optimizer-capacity',0))")
            if user_id:
                self._owner_lock(cursor, user_id, wallet=wallet)
            yield cursor

    @staticmethod
    def _owner_lock(cursor, user_id, *, wallet=True):
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("cn-resume-optimizer-owner:" + user_id,))
        if wallet:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("billing-user:" + user_id,))

    @staticmethod
    def _member(cursor, user_id, now_ms):
        cursor.execute("""SELECT entitlement_id FROM billing_time_pass_entitlements
            WHERE user_id=%s AND starts_at_ms<=%s AND ends_at_ms>%s
            ORDER BY ends_at_ms,entitlement_id LIMIT 1""", (user_id,now_ms,now_ms))
        row=cursor.fetchone()
        if row:
            return "billing:"+row["entitlement_id"]
        cursor.execute("SELECT to_regclass('admin_time_entitlements') AS name")
        if cursor.fetchone()["name"] is not None:
            cursor.execute("""SELECT entitlement_id FROM admin_time_entitlements
                WHERE user_id=%s AND starts_at_ms<=%s AND ends_at_ms>%s
                ORDER BY ends_at_ms,entitlement_id LIMIT 1""", (user_id,now_ms,now_ms))
            row=cursor.fetchone()
            if row:
                return "admin:"+row["entitlement_id"]
        return None

    @staticmethod
    def _remaining(cursor, user_id, day):
        cursor.execute("""SELECT count(*) AS used FROM cn_resume_optimizer_usage
            WHERE owner_user_id=%s AND quota_day=%s AND billing_class='daily_pass_free'
              AND status IN ('reserved','settled')""", (user_id,day))
        return max(0,DAILY_FREE_LIMIT-int(cursor.fetchone()["used"]))

    @staticmethod
    def _available(cursor,user_id):
        cursor.execute("""SELECT COALESCE((SELECT SUM(points) FROM points_redemption_ledger WHERE user_id=%s),0)
            - COALESCE((SELECT SUM(points_reserved) FROM billing_usage_reservations WHERE user_id=%s AND status='reserved'),0)
            - COALESCE((SELECT SUM(points_reserved) FROM billing_index_reservations WHERE user_id=%s AND status='reserved'),0) AS available""",
            (user_id,user_id,user_id))
        return int(cursor.fetchone()["available"])

    @classmethod
    def _quote(cls,cursor,user_id,now_ms):
        member=cls._member(cursor,user_id,now_ms)
        remaining=cls._remaining(cursor,user_id,quota_day(now_ms)) if member else 0
        free=bool(member and remaining>0)
        available=cls._available(cursor,user_id)
        return {"eligible":True,"activeTimeMember":bool(member),"dailyRemaining":remaining,
                "exhausted":bool(member and remaining==0),"billingClass":"daily_pass_free" if free else "points",
                "entryPoints":0 if free else 100,"availablePoints":available},member

    @staticmethod
    def _ledger(cursor,*,user_id,job_id,kind,points,now_ms):
        reference=f"cn-resume-optimizer:{job_id}:{'charge' if points<0 else 'refund'}"
        cursor.execute("""INSERT INTO points_redemption_ledger
            (ledger_entry_id,user_id,kind,points,created_at_ms,reference_id,description)
            VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(reference_id) DO NOTHING""",
            ("ledger-cn-resume-"+uuid4().hex,user_id,kind,points,now_ms,reference,
             "简历优化扣费" if points<0 else "简历优化未完成退还"))
        cursor.execute("SELECT user_id,kind,points FROM points_redemption_ledger WHERE reference_id=%s",(reference,))
        entry=cursor.fetchone()
        if not entry or (entry["user_id"],entry["kind"],entry["points"])!=(user_id,kind,points):
            raise RuntimeError("cn_resume_optimizer_ledger_conflict")

    @staticmethod
    def _row(cursor, *, user_id, job_id, include_deleted=False):
        cursor.execute("""SELECT j.*,u.status AS allowance_status,u.billing_class,u.points_charged FROM cn_resume_optimizer_jobs j
            JOIN cn_resume_optimizer_usage u ON u.job_id=j.job_id
            WHERE j.owner_user_id=%s AND j.job_id=%s""" + ("" if include_deleted else " AND j.deleted_at_ms IS NULL"), (user_id, job_id))
        row = cursor.fetchone()
        if not row:
            raise optimizer_error("not_found")
        return row

    @staticmethod
    def _sources_valid(cursor, row):
        expected = [(row["source_document_id"], row["source_version_id"], "resume")]
        if row.get("jd_document_id"):
            expected.append((row["jd_document_id"], row["jd_version_id"], "job_description"))
        for doc_id, version_id, kind in sorted(expected):
            cursor.execute("""SELECT d.owner_user_id,d.document_kind,d.current_version_id,d.status,d.deleted_at_ms,
                v.lifecycle_status,v.deleted_at_ms AS version_deleted,v.owner_user_id AS version_owner,
                v.document_id AS version_document,v.document_kind AS version_kind
                FROM material_documents d JOIN material_document_versions v ON v.document_version_id=d.current_version_id
                WHERE d.document_id=%s FOR SHARE OF d,v""", (doc_id,))
            source = cursor.fetchone()
            if (not source or source["owner_user_id"] != row["owner_user_id"] or source["document_kind"] != kind
                or source["current_version_id"] != version_id or source["status"] != "ready"
                or source["lifecycle_status"] != "ready" or source["deleted_at_ms"] is not None
                or source["version_deleted"] is not None or source["version_owner"] != row["owner_user_id"]
                or source["version_document"] != doc_id or source["version_kind"] != kind):
                return False
        return True

    @classmethod
    def _release(cls,cursor,job_id,now_ms):
        cursor.execute("""SELECT owner_user_id,billing_class,points_charged,status
            FROM cn_resume_optimizer_usage WHERE job_id=%s FOR UPDATE""",(job_id,))
        usage=cursor.fetchone()
        if not usage or usage["status"]!="reserved":
            return
        if usage["billing_class"]=="points":
            cls._ledger(cursor,user_id=usage["owner_user_id"],job_id=job_id,kind="resume_optimizer_refund",
                        points=int(usage["points_charged"]),now_ms=now_ms)
        cursor.execute("UPDATE cn_resume_optimizer_usage SET status='released',finalized_at_ms=%s WHERE job_id=%s AND status='reserved'",(now_ms,job_id))

    @classmethod
    def _purge(cls, cursor, row, now_ms):
        cls._release(cursor, row["job_id"], now_ms)
        cursor.execute("""UPDATE cn_resume_optimizer_jobs SET payload='{}'::jsonb, deleted_at_ms=%s,
            updated_at_ms=%s,revision=revision+1,claim_token=NULL,lease_until_ms=NULL,error_code=NULL,
            status=CASE WHEN status IN ('queued','running') THEN 'cancelled' ELSE status END
            WHERE job_id=%s AND deleted_at_ms IS NULL""", (now_ms, now_ms, row["job_id"]))

    def validate_inputs(self, *, user_id, source_document_id, source_version_id, jd_document_id, jd_version_id):
        row=dict(owner_user_id=user_id,source_document_id=source_document_id,source_version_id=source_version_id,
                 jd_document_id=jd_document_id,jd_version_id=jd_version_id)
        with self.transaction(user_id,global_lock=False,wallet=False) as cursor:
            if not self._sources_valid(cursor,row):
                raise optimizer_error("source_unavailable")

    def replay(self, *, user_id, key, fingerprint):
        with self.transaction(user_id, global_lock=False,wallet=False) as cursor:
            cursor.execute("SELECT job_id,input_fingerprint,deleted_at_ms FROM cn_resume_optimizer_jobs WHERE owner_user_id=%s AND idempotency_key=%s", (user_id, key))
            row = cursor.fetchone()
            if not row:
                return None
            if row["deleted_at_ms"] is not None:
                raise optimizer_error("not_found")
            if row["input_fingerprint"] != fingerprint:
                raise optimizer_error("idempotency_conflict")
            return self._row(cursor, user_id=user_id, job_id=row["job_id"])

    def capabilities(self,*,user_id,now_ms):
        with self.transaction(user_id,global_lock=False) as cursor:
            quote,_=self._quote(cursor,user_id,now_ms)
            cursor.execute("""SELECT job_id FROM cn_resume_optimizer_jobs WHERE owner_user_id=%s
                AND deleted_at_ms IS NULL AND status IN ('queued','running') ORDER BY created_at_ms LIMIT 1""",(user_id,))
            active=cursor.fetchone()
            quote.update(activeJobId=active["job_id"] if active else None,
                         canStart=not active and (quote["entryPoints"]==0 or quote["availablePoints"]>=100))
            return quote

    def create(self, *, user_id, key, fingerprint, source_document_id, source_version_id,
               jd_document_id, jd_version_id, payload, quoted_day, quoted_billing_class, quoted_points, confirm_points_charge, now_ms):
        with self.transaction(user_id) as cursor:
            cursor.execute("SELECT job_id,input_fingerprint,deleted_at_ms FROM cn_resume_optimizer_jobs WHERE owner_user_id=%s AND idempotency_key=%s", (user_id, key))
            old = cursor.fetchone()
            if old:
                if old["deleted_at_ms"] is not None:
                    raise optimizer_error("not_found")
                if old["input_fingerprint"] != fingerprint:
                    raise optimizer_error("idempotency_conflict")
                return self._row(cursor, user_id=user_id, job_id=old["job_id"])
            if quoted_day != quota_day(now_ms):
                raise optimizer_error("quote_changed")
            quote,member=self._quote(cursor,user_id,now_ms)
            if (quoted_billing_class,quoted_points)!=(quote["billingClass"],quote["entryPoints"]):
                raise optimizer_error("quote_changed")
            if quote["entryPoints"] and not confirm_points_charge:
                raise optimizer_error("points_confirmation_required")
            if quote["entryPoints"] and quote["availablePoints"]<quote["entryPoints"]:
                raise optimizer_error("insufficient_balance")
            cursor.execute("SELECT 1 FROM cn_resume_optimizer_jobs WHERE owner_user_id=%s AND deleted_at_ms IS NULL AND status IN ('queued','running') LIMIT 1", (user_id,))
            if cursor.fetchone():
                raise optimizer_error("busy")
            cursor.execute("SELECT count(*) AS total FROM cn_resume_optimizer_jobs WHERE deleted_at_ms IS NULL AND status IN ('queued','running')")
            if int(cursor.fetchone()["total"]) >= self.capacity:
                raise optimizer_error("busy")
            job_id = "resume-opt-" + uuid4().hex
            source = dict(source_document_id=source_document_id, source_version_id=source_version_id,
                          jd_document_id=jd_document_id, jd_version_id=jd_version_id, owner_user_id=user_id)
            if not self._sources_valid(cursor, source):
                raise optimizer_error("source_unavailable")
            cursor.execute("""INSERT INTO cn_resume_optimizer_jobs
                (job_id,owner_user_id,idempotency_key,input_fingerprint,source_document_id,source_version_id,
                 jd_document_id,jd_version_id,status,quota_day,created_at_ms,updated_at_ms,payload)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s,%s,%s)""",
                (job_id,user_id,key,fingerprint,source_document_id,source_version_id,jd_document_id,jd_version_id,
                 quoted_day,now_ms,now_ms,Jsonb(payload)))
            cursor.execute("""INSERT INTO cn_resume_optimizer_usage
                (job_id,owner_user_id,quota_day,membership_entitlement_id,billing_class,points_charged,status,created_at_ms)
                VALUES(%s,%s,%s,%s,%s,%s,'reserved',%s)""",
                (job_id,user_id,quoted_day,member if quote["entryPoints"]==0 else None,
                 quote["billingClass"],quote["entryPoints"],now_ms))
            if quote["entryPoints"]:
                self._ledger(cursor,user_id=user_id,job_id=job_id,kind="resume_optimizer_charge",points=-100,now_ms=now_ms)
            return self._row(cursor,user_id=user_id,job_id=job_id)

    def get(self, *, user_id, job_id, now_ms, require_completed=False, revision=None):
        # Explicit commit on a purge, then return an error outside its transaction.
        unavailable = False
        with self.transaction(user_id, global_lock=False) as cursor:
            row = self._row(cursor,user_id=user_id,job_id=job_id)
            if not self._sources_valid(cursor,row):
                self._purge(cursor,row,now_ms)
                unavailable = True
            elif require_completed:
                self.require_completed(row, revision)
        if unavailable:
            raise optimizer_error("not_found")
        return row

    @staticmethod
    def require_completed(row, revision=None):
        if row["status"] != "completed":
            raise optimizer_error("not_completed")
        if revision is not None and row["revision"] != revision:
            raise optimizer_error("revision_conflict")

    def list(self, *, user_id, now_ms):
        with self.transaction(user_id, global_lock=False) as cursor:
            cursor.execute("""SELECT j.*,u.status AS allowance_status,u.billing_class,u.points_charged FROM cn_resume_optimizer_jobs j
                JOIN cn_resume_optimizer_usage u ON u.job_id=j.job_id
                WHERE j.owner_user_id=%s AND j.deleted_at_ms IS NULL ORDER BY j.created_at_ms DESC,j.job_id DESC LIMIT 30""", (user_id,))
            rows = cursor.fetchall()
            valid=[]
            for row in rows:
                if self._sources_valid(cursor,row):
                    valid.append(row)
                else:
                    self._purge(cursor,row,now_ms)
            return valid

    def cancel(self, *, user_id, job_id, now_ms):
        with self.transaction(user_id) as cursor:
            row = self._row(cursor,user_id=user_id,job_id=job_id)
            if row["status"] in ("queued","running"):
                cursor.execute("UPDATE cn_resume_optimizer_jobs SET status='cancelled',revision=revision+1,updated_at_ms=%s,lease_until_ms=NULL,claim_token=NULL WHERE job_id=%s", (now_ms,job_id))
                self._release(cursor,job_id,now_ms)
            return self._row(cursor,user_id=user_id,job_id=job_id)

    def delete(self, *, user_id, job_id, now_ms):
        with self.transaction(user_id) as cursor:
            row = self._row(cursor,user_id=user_id,job_id=job_id,include_deleted=True)
            self._purge(cursor,row,now_ms)

    def purge_by_source(self, *, user_id, document_id, now_ms, delete_source=False):
        with self.transaction(user_id) as cursor:
            if delete_source:
                # The document and optimizer content become unavailable in one
                # durable transaction, before the existing cleanup is scheduled.
                cursor.execute("UPDATE material_documents SET status='deleted',deleted_at_ms=%s,updated_at_ms=%s WHERE document_id=%s AND owner_user_id=%s", (now_ms,now_ms,document_id,user_id))
                cursor.execute("UPDATE material_document_versions SET lifecycle_status='deleted',index_state='deleted',deleted_at_ms=%s,updated_at_ms=%s WHERE document_id=%s AND owner_user_id=%s", (now_ms,now_ms,document_id,user_id))
            cursor.execute("SELECT * FROM cn_resume_optimizer_jobs WHERE owner_user_id=%s AND deleted_at_ms IS NULL AND (source_document_id=%s OR jd_document_id=%s)", (user_id,document_id,document_id))
            for row in cursor.fetchall():
                self._purge(cursor,row,now_ms)

    def claim(self, *, now_ms):
        with self.transaction() as cursor:
            cursor.execute("SELECT 1 FROM cn_resume_optimizer_jobs WHERE status='running' AND deleted_at_ms IS NULL LIMIT 1")
            if cursor.fetchone():
                return None
            cursor.execute("SELECT * FROM cn_resume_optimizer_jobs WHERE status='queued' AND deleted_at_ms IS NULL ORDER BY created_at_ms,job_id LIMIT 1")
            row=cursor.fetchone()
            if not row:
                return None
            self._owner_lock(cursor,row["owner_user_id"])
            if not self._sources_valid(cursor,row):
                self._purge(cursor,row,now_ms)
                return None
            token=uuid4().hex
            cursor.execute("UPDATE cn_resume_optimizer_jobs SET status='running',claim_token=%s,lease_until_ms=%s,updated_at_ms=%s WHERE job_id=%s AND status='queued' AND deleted_at_ms IS NULL", (token,now_ms+self.lease_ms,now_ms,row["job_id"]))
            return self._row(cursor,user_id=row["owner_user_id"],job_id=row["job_id"])

    def finish(self, *, user_id, job_id, token, revision, now_ms, review=None, draft=None, error=None, diagnostic=None):
        with self.transaction(user_id) as cursor:
            try:
                row=self._row(cursor,user_id=user_id,job_id=job_id)
            except DomainRequestError:
                return False
            if row["status"] != "running" or row["claim_token"] != token or row["revision"] != revision:
                return False
            if not self._sources_valid(cursor,row):
                self._purge(cursor,row,now_ms)
                return False
            if row["lease_until_ms"] < now_ms:
                error="interrupted"
                diagnostic=failure_diagnostic("runtime_interrupted")
            if error:
                self._release(cursor,job_id,now_ms)
                payload={**row["payload"]}
                # Persist fixed codes only, after the same claim/source guards
                # as the terminal financial update. Late failures cannot revive
                # deleted or cancelled content or overwrite a prior result.
                payload.pop("failureDiagnostic",None)
                safe_diagnostic=normalize_failure_diagnostic(diagnostic)
                if safe_diagnostic:
                    payload["failureDiagnostic"]=safe_diagnostic
                cursor.execute("""UPDATE cn_resume_optimizer_jobs SET status='failed',revision=revision+1,
                    updated_at_ms=%s,lease_until_ms=NULL,claim_token=NULL,error_code=%s,payload=%s
                    WHERE job_id=%s""",(now_ms,error,Jsonb(payload),job_id))
            else:
                payload={**row["payload"],"review":review,"initialDraftMarkdown":draft,"draftMarkdown":draft}
                cursor.execute("""UPDATE cn_resume_optimizer_jobs SET status='completed',revision=revision+1,
                    updated_at_ms=%s,completed_at_ms=%s,lease_until_ms=NULL,claim_token=NULL,payload=%s,error_code=NULL
                    WHERE job_id=%s""",(now_ms,now_ms,Jsonb(payload),job_id))
                cursor.execute("UPDATE cn_resume_optimizer_usage SET status='settled',finalized_at_ms=%s WHERE job_id=%s AND status='reserved'", (now_ms,job_id))
            return True

    def reap(self, *, now_ms):
        with self.transaction() as cursor:
            cursor.execute("""SELECT * FROM cn_resume_optimizer_jobs WHERE deleted_at_ms IS NULL AND
                ((status='running' AND lease_until_ms<%s) OR (status='queued' AND created_at_ms<%s))""", (now_ms,now_ms-self.queue_lifetime_ms))
            rows=cursor.fetchall()
            for row in rows:
                self._owner_lock(cursor,row["owner_user_id"])
                self._release(cursor,row["job_id"],now_ms)
                cursor.execute("""UPDATE cn_resume_optimizer_jobs SET status='failed',revision=revision+1,error_code='interrupted',
                    updated_at_ms=%s,lease_until_ms=NULL,claim_token=NULL WHERE job_id=%s AND status IN ('queued','running')""", (now_ms,row["job_id"]))
            return len(rows)

    def update_draft(self, *, user_id, job_id, revision, markdown, now_ms):
        with self.transaction(user_id,global_lock=False,wallet=False) as cursor:
            row=self._row(cursor,user_id=user_id,job_id=job_id)
            self.require_completed(row,revision)
            if not self._sources_valid(cursor,row):
                raise optimizer_error("source_unavailable")
            payload={**row["payload"],"draftMarkdown":markdown,"savedDocumentId":None,"savedVersionId":None}
            cursor.execute("UPDATE cn_resume_optimizer_jobs SET revision=revision+1,updated_at_ms=%s,payload=%s WHERE job_id=%s", (now_ms,Jsonb(payload),job_id))
            return self._row(cursor,user_id=user_id,job_id=job_id)

    def save_as(self, *, user_id, job_id, revision, now_ms, save_callback):
        with self.transaction(user_id,global_lock=False,wallet=False) as cursor:
            row=self._row(cursor,user_id=user_id,job_id=job_id)
            self.require_completed(row,revision)
            if not self._sources_valid(cursor,row):
                raise optimizer_error("source_unavailable")
            payload=row["payload"]
            # The callback uses deterministic ids and bounded private object I/O,
            # no provider request; held source-row shares serialize deletion.
            result=save_callback(row)
            payload={**payload,"savedDocumentId":result.document_id,"savedVersionId":result.document_version_id}
            cursor.execute("UPDATE cn_resume_optimizer_jobs SET payload=%s,updated_at_ms=%s WHERE job_id=%s", (Jsonb(payload),now_ms,job_id))
            return result
