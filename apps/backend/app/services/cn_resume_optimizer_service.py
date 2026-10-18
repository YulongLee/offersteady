"""Owned optimizer input/read/edit/export orchestration and isolated runner."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import hashlib
import logging
import re
from time import monotonic, time
from uuid import uuid5, NAMESPACE_URL

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.document_repository import DocumentRecord
from app.schemas.cn_resume_optimizer import CreateResumeOptimization
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.cn_resume_optimizer_source import normalize_optimizer_source, UnsupportedResumeMarkup
from app.services.cn_resume_optimizer_diagnostics import (error_message_for_diagnostic,
    failure_diagnostic, normalize_failure_diagnostic)
from app.services.cn_resume_optimizer_provider import (PROMPT_VERSION, SCORE_VERSION, ResumeProviderError,
    CNResumeOptimizerProvider, validate_plain_text)
from app.services.cn_resume_optimizer_repository import (CNResumeOptimizerRepository, optimizer_error,
    DAILY_FREE_LIMIT, input_fingerprint, quota_day, reset_at)


def now_ms():
    return int(time() * 1000)


SAFE_ERRORS = {
    "invalid_output": "未生成可靠的优化稿，本次积分或免费次数已退还，请重试。",
    "provider_timeout": "简历优化超时，本次积分或免费次数已退还，请重试。",
    "provider_unavailable": "简历优化服务暂不可用，本次积分或免费次数已退还。",
    "provider_unconfigured": "简历优化服务暂不可用，本次积分或免费次数已退还。",
    "interrupted": "本次优化已中断，积分或免费次数已退还，请重新发起。",
    "source_unavailable": "所选原始资料已失效，本次积分或免费次数已退还。",
}


def public_job(row, *, detail=True):
    payload=row["payload"]
    error_message=SAFE_ERRORS.get(row["error_code"]) if row["error_code"] else None
    if row["status"]=="failed" and row["error_code"]:
        diagnostic_message=error_message_for_diagnostic(payload.get("failureDiagnostic"))
        if diagnostic_message:
            error_message=diagnostic_message
            if row["allowance_status"]=="released":
                error_message+="本次积分或免费次数已退还。"
    result={"jobId":row["job_id"],"status":row["status"],"revision":row["revision"],
        "sourceDocumentId":row["source_document_id"],"sourceVersionId":row["source_version_id"],
        "sourceDisplayName":payload.get("sourceDisplayName","简历"),"targetRole":payload.get("targetRole",""),
        "hasJd":bool(payload.get("jdText")),"quotaDay":str(row["quota_day"]),
        "allowanceStatus":row["allowance_status"],"billingStatus":row["allowance_status"],
        "billingClass":row["billing_class"],"pointsCharged":int(row["points_charged"]),"createdAtMs":row["created_at_ms"],
        "updatedAtMs":row["updated_at_ms"],"completedAtMs":row["completed_at_ms"],
        "errorCode":row["error_code"],"errorMessage":error_message,
        "savedDocumentId":payload.get("savedDocumentId"),"savedVersionId":payload.get("savedVersionId")}
    if detail:
        result.update(sourceText=payload.get("sourceText",""),jdText=payload.get("jdText",""),
            jdDocumentId=row["jd_document_id"],jdVersionId=row["jd_version_id"],
            review=payload.get("review"),initialDraftMarkdown=payload.get("initialDraftMarkdown"),
            draftMarkdown=payload.get("draftMarkdown"),promptVersion=payload.get("promptVersion",PROMPT_VERSION),
            scoreVersion=payload.get("scoreVersion",SCORE_VERSION))
    return result


class CNResumeOptimizerService:
    def __init__(self, *, settings, repository, documents, storage, document_service=None,
                 provider=None, clock=now_ms, exporter=None):
        self.settings=settings
        self.repository=repository
        self.documents=documents
        self.storage=storage
        self.document_service=document_service
        self.provider=provider or CNResumeOptimizerProvider(settings)
        self.clock=clock
        self.exporter=exporter
        self.runtime=None

    def enabled(self):
        return (self.settings.product_edition=="cn" and self.settings.cn_resume_optimizer_enabled
                and bool(self.settings.chat_qwen_api_key and self.settings.chat_qwen_base_url))

    def require_enabled(self):
        if not self.enabled():
            raise optimizer_error("disabled")

    def capabilities(self,user_id):
        now=self.clock()
        base={"enabled":self.enabled(),"eligible":True,"dailyLimit":DAILY_FREE_LIMIT,"dailyRemaining":0,
              "quotaDay":quota_day(now),"timezone":"Asia/Shanghai","resetAtMs":reset_at(now),"nowMs":now,
              "memberRequired":False,"activeTimeMember":False,"exhausted":False,"activeJobId":None,
              "billingClass":"points","entryPoints":100,"availablePoints":0,"canStart":False,
              "limits":{"resumeCharacters":40000,"jdCharacters":12000,"targetRoleCharacters":120,"draftCharacters":60000},
              "exports":["docx","pdf"]}
        if base["enabled"]:
            base.update(self.repository.capabilities(user_id=user_id,now_ms=now))
        return base

    def _read_source(self, *, user_id, document_id, version_id, kind, max_chars):
        doc=self.documents.get_by_id(document_id)
        if (not doc or doc.owner_user_id!=user_id or doc.document_kind!=kind or doc.status!="ready"
            or doc.deleted_at_ms is not None or doc.document_version_id!=version_id):
            raise optimizer_error("source_unavailable")
        key=MaterialObjectKeyFactory(self.settings).processed_artifact_key(owner_user_id=user_id,
            document_kind=kind,document_id=document_id,document_version_id=version_id,artifact_kind="normalized_markdown")
        try:
            raw=self.storage.load_object_bytes(object_key=key)
            if len(raw)>2*1024*1024:
                raise ValueError()
            text=raw.decode("utf-8").strip()
        except Exception:
            raise optimizer_error("source_unavailable") from None
        try:
            text=normalize_optimizer_source(text)
        except UnsupportedResumeMarkup:
            raise optimizer_error("source_markup_unsupported") from None
        if not text or len(text)>max_chars or "\x00" in text:
            raise optimizer_error("source_unavailable")
        return doc,text

    def create(self, user_id: str, request: CreateResumeOptimization):
        self.require_enabled()
        # The day is a quote confirmation, not part of material idempotency.
        logical=request.model_dump(exclude={"quoted_quota_day","quoted_billing_class","quoted_points","confirm_points_charge","confirm_processing","idempotency_key"})
        fingerprint=input_fingerprint(logical)
        old=self.repository.replay(user_id=user_id,key=request.idempotency_key,fingerprint=fingerprint)
        if old:
            return self.get(user_id,old["job_id"])
        cap=self.capabilities(user_id)
        if request.quoted_quota_day!=cap["quotaDay"]:
            raise optimizer_error("quote_changed")
        if (request.quoted_billing_class,request.quoted_points)!=(cap["billingClass"],cap["entryPoints"]):
            raise optimizer_error("quote_changed")
        if cap["entryPoints"] and not request.confirm_points_charge:
            raise optimizer_error("points_confirmation_required")
        if cap["entryPoints"] and cap["availablePoints"]<100:
            raise optimizer_error("insufficient_balance")
        self.repository.validate_inputs(user_id=user_id,source_document_id=request.source_document_id,
            source_version_id=request.source_version_id,jd_document_id=request.jd_document_id,jd_version_id=request.jd_version_id)
        doc,text=self._read_source(user_id=user_id,document_id=request.source_document_id,
            version_id=request.source_version_id,kind="resume",max_chars=40000)
        try:
            jd=normalize_optimizer_source(request.jd_text) if request.jd_text else ""
        except UnsupportedResumeMarkup:
            raise optimizer_error("source_markup_unsupported") from None
        if request.jd_document_id:
            _,jd=self._read_source(user_id=user_id,document_id=request.jd_document_id,
                version_id=request.jd_version_id,kind="job_description",max_chars=12000)
        row=self.repository.create(user_id=user_id,key=request.idempotency_key,fingerprint=fingerprint,
            source_document_id=request.source_document_id,source_version_id=request.source_version_id,
            jd_document_id=request.jd_document_id,jd_version_id=request.jd_version_id,
            payload={"sourceText":text,"jdText":jd,"targetRole":request.target_role,"sourceDisplayName":doc.display_name,
                     "promptVersion":PROMPT_VERSION,"scoreVersion":SCORE_VERSION,"providerModel":self.settings.chat_qwen_model},
            quoted_day=request.quoted_quota_day,quoted_billing_class=request.quoted_billing_class,
            quoted_points=request.quoted_points,confirm_points_charge=request.confirm_points_charge,now_ms=self.clock())
        if self.runtime:
            self.runtime.wake()
        return public_job(row)

    def get(self,user_id,job_id):
        self.require_enabled()
        return public_job(self.repository.get(user_id=user_id,job_id=job_id,now_ms=self.clock()))

    def list(self,user_id):
        self.require_enabled()
        return {"jobs":[public_job(r,detail=False) for r in self.repository.list(user_id=user_id,now_ms=self.clock())]}

    def cancel(self,user_id,job_id):
        self.require_enabled()
        row=self.repository.cancel(user_id=user_id,job_id=job_id,now_ms=self.clock())
        if self.runtime:
            self.runtime.cancel_active(job_id)
        return self.get(user_id,job_id)

    def delete(self,user_id,job_id):
        self.require_enabled()
        self.repository.delete(user_id=user_id,job_id=job_id,now_ms=self.clock())
        if self.runtime:
            self.runtime.cancel_active(job_id)
        return {"deleted":True}

    def update_draft(self,user_id,job_id,*,revision,markdown):
        self.require_enabled()
        try:
            markdown=validate_plain_text(markdown)
        except ResumeProviderError:
            raise optimizer_error("invalid_draft") from None
        row=self.repository.update_draft(user_id=user_id,job_id=job_id,revision=revision,markdown=markdown,now_ms=self.clock())
        return public_job(row)

    def export(self,user_id,job_id,*,revision,format,facts_confirmed):
        self.require_enabled()
        if not facts_confirmed or format not in ("docx","pdf"):
            raise optimizer_error("invalid_draft")
        row=self.repository.get(user_id=user_id,job_id=job_id,now_ms=self.clock(),require_completed=True,revision=revision)
        renderer=self.exporter
        if renderer is None:
            from app.services.resume_optimizer_export import render_resume_export
            renderer=render_resume_export
        try:
            output=renderer(row["payload"]["draftMarkdown"],format)
        except ValueError:
            raise DomainRequestError("resume-optimizer", "export", "当前简历无法导出此格式，请尝试 Word（DOCX），或编辑不支持的字符后重试。", 422,
                                     error_code="resume_optimizer_export_unavailable") from None
        except (ImportError, RuntimeError):
            raise DomainRequestError("resume-optimizer", "export", "简历导出暂不可用，请稍后重试。", 503,
                                     error_code="resume_optimizer_export_unavailable") from None
        # No result can be delivered after an already committed deletion/update.
        self.repository.get(user_id=user_id,job_id=job_id,now_ms=self.clock(),require_completed=True,revision=revision)
        return output

    def save_as(self,user_id,job_id,*,revision,facts_confirmed):
        self.require_enabled()
        if not facts_confirmed or self.document_service is None:
            raise optimizer_error("invalid_draft")
        def save(row):
            stable=uuid5(NAMESPACE_URL,f"offersteady:cn-resume-optimizer:{user_id}:{job_id}:{revision}").hex
            return self.document_service.create_optimized_resume(user_id=user_id,
                markdown=row["payload"]["draftMarkdown"],stable_id=stable)
        return self.repository.save_as(user_id=user_id,job_id=job_id,revision=revision,now_ms=self.clock(),save_callback=save)


class CNResumeOptimizerRuntime:
    """One independent async provider with a separate small DB/storage executor."""
    def __init__(self,service):
        self.service=service
        service.runtime=self
        self.executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix="resume-optimizer")
        self.loop=None
        self.event=None
        self.runner=None
        self.active=None
        self.active_job_id=None
        self.active_source_ids=()
        self.closed=False
        self.logger=logging.getLogger("offersteady.resume-optimizer")

    async def db(self,fn,*args,**kwargs):
        return await asyncio.get_running_loop().run_in_executor(self.executor,partial(fn,*args,**kwargs))

    async def start(self):
        self.loop=asyncio.get_running_loop()
        self.event=asyncio.Event()
        await self.db(self.service.repository.reap,now_ms=self.service.clock())
        self.runner=asyncio.create_task(self._run(),name="cn-resume-optimizer")

    def wake(self):
        if self.loop and self.event and not self.closed:
            self.loop.call_soon_threadsafe(self.event.set)

    def cancel_active(self,job_id):
        if self.loop and self.active_job_id==job_id and self.active:
            self.loop.call_soon_threadsafe(self.active.cancel)

    def cancel_active_for_source(self,document_id):
        if document_id in self.active_source_ids and self.active_job_id:
            self.cancel_active(self.active_job_id)

    async def _execute(self,row):
        started=monotonic()
        args=dict(user_id=row["owner_user_id"],job_id=row["job_id"],token=row["claim_token"],revision=row["revision"])
        async def fail(code, diagnostic):
            failed_at=self.service.clock()
            if row["lease_until_ms"]<failed_at:
                code="interrupted"
                diagnostic=failure_diagnostic("runtime_interrupted")
            committed=await self.db(self.service.repository.finish,**args,now_ms=failed_at,
                error=code,diagnostic=diagnostic)
            if committed:
                safe_diagnostic=normalize_failure_diagnostic(diagnostic)
                log_event(self.logger,logging.WARNING,settings=self.service.settings,
                    event="resume_optimizer_task_failed",errorCategory=code,
                    diagnostic=safe_diagnostic,durationMs=max(0,int((monotonic()-started)*1000)))
        try:
            # Re-read guards immediately before sending any personal content.
            fresh=await self.db(self.service.repository.get,user_id=args["user_id"],job_id=args["job_id"],now_ms=self.service.clock())
            if fresh["status"]!="running" or fresh["claim_token"]!=args["token"]:
                return
            async with asyncio.timeout(self.service.settings.cn_resume_optimizer_timeout_seconds):
                review,draft=await self.service.provider.generate(resume=fresh["payload"]["sourceText"],
                    jd=fresh["payload"]["jdText"],target_role=fresh["payload"]["targetRole"])
            await self.db(self.service.repository.finish,**args,now_ms=self.service.clock(),review=review,draft=draft)
        except asyncio.CancelledError:
            # Cancellation never revives a task; conditional finish is safe if
            # user/source deletion already cleared it in another transaction.
            await asyncio.shield(fail("interrupted",failure_diagnostic("runtime_interrupted")))
            raise
        except (ResumeProviderError,TimeoutError) as exc:
            code=exc.category if isinstance(exc,ResumeProviderError) else "provider_timeout"
            diagnostic=exc.diagnostic if isinstance(exc,ResumeProviderError) else failure_diagnostic("runtime_timeout")
            await fail(code,diagnostic)
        except Exception:
            await fail("interrupted",failure_diagnostic("runtime_internal_error"))

    async def _run(self):
        while not self.closed:
            # Clear before the DB poll so a creation committed during the poll
            # cannot lose its wake and wait for the three-second fallback.
            self.event.clear()
            try:
                await self.db(self.service.repository.reap,now_ms=self.service.clock())
                row=await self.db(self.service.repository.claim,now_ms=self.service.clock())
                if row:
                    self.active_job_id=row["job_id"]
                    self.active_source_ids=(row["source_document_id"],row["jd_document_id"])
                    self.active=asyncio.create_task(self._execute(row),name="resume-optimizer-generation")
                    try:
                        await self.active
                    except asyncio.CancelledError:
                        if self.closed:
                            raise
                    finally:
                        self.active=None
                        self.active_job_id=None
                        self.active_source_ids=()
                    continue
            except asyncio.CancelledError:
                raise
            except Exception:
                log_event(self.logger,logging.WARNING,settings=self.service.settings,event="resume_optimizer_poll_failed",
                    errorCategory="repository_unavailable",diagnostic=failure_diagnostic("runtime_repository_unavailable"))
            try:
                await asyncio.wait_for(self.event.wait(),timeout=3)
            except TimeoutError:
                pass

    async def shutdown(self):
        self.closed=True
        if self.runner:
            self.runner.cancel()
            await asyncio.gather(self.runner,return_exceptions=True)
        self.executor.shutdown(wait=True,cancel_futures=True)
        self.service.runtime=None
