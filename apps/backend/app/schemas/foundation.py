from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class RuntimeDependencyStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    configured: bool
    healthy: bool
    message: str


class RuntimeVectorStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    configured: bool
    extensionAvailable: bool
    message: str


class RuntimeRetrievalStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    retrievalPort: str
    pgvectorSchema: str
    extensionName: str


class RuntimeOverviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    database: RuntimeDependencyStatus
    objectStorage: RuntimeDependencyStatus
    pgvector: RuntimeVectorStatus
    retrieval: RuntimeRetrievalStatus


class ModuleDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    feature: str
    owning_app: str = Field(alias="owningApp")
    route_prefix: str = Field(alias="routePrefix")
    mode: Literal["placeholder", "reference-only", "deferred", "active"]
    notes: str


class FoundationIndexResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    service: str
    api_prefix: str = Field(alias="apiPrefix")
    prototype_mode: str = Field(alias="prototypeMode")
    modules: list[ModuleDescriptor] = Field(default_factory=list)


class PlaceholderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    status: Literal["placeholder"]
    feature: str
    action: str
    message: str


class OwnershipDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    app: str
    responsibilities: list[str] = Field(default_factory=list)
    phase: Literal["now", "later", "reference-only"]


class ApiErrorDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    code: str
    message: str
    details: dict[str, object] | None = None


class ApiMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    apiVersion: str
    timestamp: str


class ApiEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    success: bool
    data: T | None = None
    error: ApiErrorDetail | None = None
    requestId: str
    meta: ApiMeta
