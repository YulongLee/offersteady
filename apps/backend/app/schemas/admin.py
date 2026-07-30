from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(item.capitalize() for item in tail)


class AdminModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


class AdminSessionRequest(AdminModel):
    access_token: str = Field(min_length=20)
    totp_code: str = Field(pattern=r"^\d{6}$")


class AdminStepUpRequest(AdminModel):
    totp_code: str = Field(pattern=r"^\d{6}$")


class AdminActionRequest(AdminModel):
    reason: str = Field(min_length=6, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)
    confirmed: bool = False


class AdminPointsAdjustmentRequest(AdminActionRequest):
    points: int = Field(ge=-1000000, le=1000000)


class AdminTimeAdjustmentRequest(AdminActionRequest):
    days: int = Field(ge=1, le=365)


class AdminCreateRequest(AdminActionRequest):
    login_id: str = Field(min_length=3, max_length=128)
    role: str = Field(pattern=r"^(super_admin|operations|support|finance|technical_auditor)$")
