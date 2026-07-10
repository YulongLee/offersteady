from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.routers import create_system_router
from app.core.config import Settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import settings_dependency
from app.modules import authentication, billing, document_processing, document_service, job_description, knowledge, knowledge_retrieval, live_answer, realtime_speech, resume, screenshot_answer, session, system, web
from app.schemas.foundation import ApiEnvelope, FoundationIndexResponse


module_descriptors = [
    session.descriptor,
    authentication.descriptor,
    document_service.descriptor,
    resume.descriptor,
    job_description.descriptor,
    knowledge.descriptor,
    knowledge_retrieval.descriptor,
    document_processing.descriptor,
    live_answer.descriptor,
    realtime_speech.descriptor,
    screenshot_answer.descriptor,
    billing.descriptor,
    web.descriptor,
]

api_router = APIRouter()
api_router.include_router(create_system_router(module_descriptors))
api_router.include_router(session.router)
api_router.include_router(authentication.router)
api_router.include_router(document_service.router)
api_router.include_router(document_processing.router)
api_router.include_router(resume.router)
api_router.include_router(job_description.router)
api_router.include_router(knowledge.router)
api_router.include_router(knowledge_retrieval.router)
api_router.include_router(live_answer.router)
api_router.include_router(realtime_speech.router)
api_router.include_router(screenshot_answer.router)
api_router.include_router(billing.router)
api_router.include_router(web.router)


@api_router.get("", response_model=ApiEnvelope[FoundationIndexResponse])
async def api_root(request: Request, settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[FoundationIndexResponse]:
    return success_response(
        request=request,
        data=FoundationIndexResponse(
            service=settings.app_name,
            api_prefix=settings.api_prefix,
            prototype_mode=settings.prototype_mode,
            modules=module_descriptors,
        ),
        timestamp=utc_now_iso(),
    )
