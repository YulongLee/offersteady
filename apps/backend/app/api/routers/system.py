from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import database_runtime, object_storage_runtime, pgvector_runtime, settings_dependency
from app.platform.database import DatabaseRuntime
from app.platform.object_storage import ObjectStorageRuntime
from app.platform.pgvector import PgvectorRuntime
from app.platform.retrieval_boundary import describe_retrieval_boundary
from app.schemas.foundation import (
    ApiEnvelope,
    FoundationIndexResponse,
    ModuleDescriptor,
    OwnershipDescriptor,
    RuntimeDependencyStatus,
    RuntimeOverviewResponse,
    RuntimeRetrievalStatus,
    RuntimeVectorStatus,
)


def create_system_router(module_descriptors: list[ModuleDescriptor]) -> APIRouter:
    router = APIRouter(prefix="/system", tags=["system"])

    @router.get("/foundation", response_model=ApiEnvelope[FoundationIndexResponse])
    async def foundation_index(request: Request, settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[FoundationIndexResponse]:
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

    @router.get("/ownership", response_model=ApiEnvelope[list[OwnershipDescriptor]])
    async def ownership(request: Request) -> ApiEnvelope[list[OwnershipDescriptor]]:
        return success_response(
            request=request,
            data=[
                OwnershipDescriptor(
                    app="apps/web",
                    phase="now",
                    responsibilities=[
                        "Keep approved prototype page structure and interaction flow",
                        "Provide UI adapters for fixture mode and backend mode",
                    ],
                ),
                OwnershipDescriptor(
                    app="apps/backend",
                    phase="now",
                    responsibilities=[
                        "Provide FastAPI platform conventions, versioned APIs, middleware, and feature routers",
                        "Reserve extension points for storage, parsing, retrieval, generation, screenshot analysis, and streaming",
                    ],
                ),
                OwnershipDescriptor(
                    app="packages/protocol",
                    phase="now",
                    responsibilities=[
                        "Host shared transport contracts and placeholder DTO locations",
                    ],
                ),
                OwnershipDescriptor(
                    app="packages/config",
                    phase="now",
                    responsibilities=[
                        "Host shared public runtime configuration keys and logging field conventions",
                    ],
                ),
                OwnershipDescriptor(
                    app="apps/api",
                    phase="reference-only",
                    responsibilities=[
                        "Keep TypeScript prototype service behavior as reference and contract sample during migration",
                    ],
                ),
                OwnershipDescriptor(
                    app="apps/desktop",
                    phase="later",
                    responsibilities=[
                        "Bridge authorized local device capture into web sessions in a later phase",
                    ],
                ),
            ],
            timestamp=utc_now_iso(),
        )

    @router.get("/runtime", response_model=ApiEnvelope[RuntimeOverviewResponse])
    async def runtime_overview(
        request: Request,
        settings: Settings = Depends(settings_dependency),
        database: DatabaseRuntime = Depends(database_runtime),
        object_storage: ObjectStorageRuntime = Depends(object_storage_runtime),
        pgvector: PgvectorRuntime = Depends(pgvector_runtime),
    ) -> ApiEnvelope[RuntimeOverviewResponse]:
        db_status = database.check_health()
        oss_status = object_storage.check_health()
        vector_status = pgvector.check_extension()
        retrieval = describe_retrieval_boundary(settings)
        return success_response(
            request=request,
            data=RuntimeOverviewResponse(
                database=RuntimeDependencyStatus(
                    configured=db_status.configured,
                    healthy=db_status.healthy,
                    message=db_status.message,
                ),
                objectStorage=RuntimeDependencyStatus(
                    configured=oss_status.configured,
                    healthy=oss_status.healthy,
                    message=oss_status.message,
                ),
                pgvector=RuntimeVectorStatus(
                    configured=vector_status.configured,
                    extensionAvailable=vector_status.extension_available,
                    message=vector_status.message,
                ),
                retrieval=RuntimeRetrievalStatus(
                    retrievalPort=retrieval.retrieval_port,
                    pgvectorSchema=retrieval.pgvector_schema,
                    extensionName=retrieval.extension_name,
                ),
            ),
            timestamp=utc_now_iso(),
        )

    return router
