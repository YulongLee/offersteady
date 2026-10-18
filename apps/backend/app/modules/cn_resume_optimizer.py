"""Authenticated CN resume optimization, isolated from interview services."""
from __future__ import annotations
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.config import get_settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import require_authenticated_context, cn_resume_optimizer_service
from app.schemas.cn_resume_optimizer import CreateResumeOptimization, UpdateResumeDraft, SaveOptimizedResume
from app.services.cn_resume_optimizer_repository import DAILY_FREE_LIMIT, optimizer_error, quota_day, reset_at
from app.services.cn_resume_optimizer_service import now_ms

router=APIRouter(prefix="/resume-optimizer",tags=["resume-optimizer"])


def enabled():
    settings=get_settings()
    return (settings.product_edition=="cn" and settings.cn_resume_optimizer_enabled
        and bool(settings.chat_qwen_api_key and settings.chat_qwen_base_url))


def require_service():
    if not enabled():
        raise optimizer_error("disabled")
    return cn_resume_optimizer_service()


def envelope(request,response,data):
    response.headers["Cache-Control"]="private, no-store"
    return success_response(request=request,data=data,timestamp=utc_now_iso())


@router.get("/capabilities")
def capabilities(request:Request,response:Response,auth=Depends(require_authenticated_context)):
    if enabled():
        data=cn_resume_optimizer_service().capabilities(auth.user_id)
    else:
        now=now_ms()
        data={"enabled":False,"eligible":True,"dailyLimit":DAILY_FREE_LIMIT,"dailyRemaining":0,"quotaDay":quota_day(now),
            "timezone":"Asia/Shanghai","resetAtMs":reset_at(now),"nowMs":now,"memberRequired":False,
            "activeTimeMember":False,"exhausted":False,"activeJobId":None,"billingClass":"points",
            "entryPoints":100,"availablePoints":0,"canStart":False,
            "limits":{"resumeCharacters":40000,"jdCharacters":12000,"targetRoleCharacters":120,"draftCharacters":60000},
            "exports":["docx","pdf"]}
    return envelope(request,response,data)


@router.post("/jobs")
def create_job(payload:CreateResumeOptimization,request:Request,response:Response,
               auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.create(auth.user_id,payload))


@router.get("/jobs")
def list_jobs(request:Request,response:Response,auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.list(auth.user_id))


@router.get("/jobs/{job_id}")
def get_job(job_id:str,request:Request,response:Response,auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.get(auth.user_id,job_id))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id:str,request:Request,response:Response,auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.cancel(auth.user_id,job_id))


@router.delete("/jobs/{job_id}")
def delete_job(job_id:str,request:Request,response:Response,auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.delete(auth.user_id,job_id))


@router.patch("/jobs/{job_id}/draft")
def update_draft(job_id:str,payload:UpdateResumeDraft,request:Request,response:Response,
                 auth=Depends(require_authenticated_context),service=Depends(require_service)):
    return envelope(request,response,service.update_draft(auth.user_id,job_id,revision=payload.expected_revision,markdown=payload.markdown))


@router.post("/jobs/{job_id}/save-as")
def save_as(job_id:str,payload:SaveOptimizedResume,request:Request,response:Response,
            auth=Depends(require_authenticated_context),service=Depends(require_service)):
    document=service.save_as(auth.user_id,job_id,revision=payload.expected_revision,facts_confirmed=payload.facts_confirmed)
    return envelope(request,response,{"document":document})


@router.get("/jobs/{job_id}/export")
def export(job_id:str,format:str=Query(pattern="^(docx|pdf)$"),expected_revision:int=Query(ge=1,alias="expectedRevision"),
           facts_confirmed:bool=Query(default=False,alias="factsConfirmed"),
           auth=Depends(require_authenticated_context),service=Depends(require_service)):
    payload,mime,filename=service.export(auth.user_id,job_id,revision=expected_revision,format=format,facts_confirmed=facts_confirmed)
    return Response(content=payload,media_type=mime,headers={"Content-Disposition":f"attachment; filename=optimized-resume.{format}; filename*=UTF-8''{quote(filename,safe='')}",
        "Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


class CNResumeOptimizerPrivacyMiddleware:
    """Add no-store to this feature only, including auth/validation errors."""
    def __init__(self,app,api_prefix):
        self.app=app
        self.prefix=api_prefix.rstrip("/")+"/resume-optimizer"

    async def __call__(self,scope,receive,send):
        if scope.get("type")!="http" or not (scope.get("path","")==self.prefix or scope.get("path","").startswith(self.prefix+"/")):
            return await self.app(scope,receive,send)
        async def send_private(message):
            if message["type"]=="http.response.start":
                message={**message,"headers":[(k,v) for k,v in message.get("headers",[]) if k.lower()!=b"cache-control"]+[(b"cache-control",b"private, no-store")]}
            await send(message)
        await self.app(scope,receive,send_private)
