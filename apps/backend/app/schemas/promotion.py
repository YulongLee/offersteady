from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(item.capitalize() for item in tail)


class PromotionModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="forbid")


class PromotionChannelCreate(PromotionModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,39}$")
    name: str = Field(min_length=1, max_length=80)
    sort_order: int = Field(default=0, ge=-10_000, le=10_000)


class PromotionChannelUpdate(PromotionModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    sort_order: int | None = Field(default=None, ge=-10_000, le=10_000)
    status: Literal["active", "inactive"] | None = None
    reason: str = Field(min_length=3, max_length=500)


class PromotionCampaignCreate(PromotionModel):
    name: str = Field(min_length=1, max_length=120)
    objective: str = Field(default="", max_length=500)
    status: Literal["draft", "active", "paused", "ended"] = "draft"
    starts_at_ms: int | None = Field(default=None, ge=0)
    ends_at_ms: int | None = Field(default=None, ge=0)
    budget_cents: int | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def valid_period(self):
        if self.starts_at_ms is not None and self.ends_at_ms is not None and self.ends_at_ms <= self.starts_at_ms:
            raise ValueError("endsAtMs must be later than startsAtMs")
        return self


class PromotionCampaignUpdate(PromotionCampaignCreate):
    reason: str = Field(min_length=3, max_length=500)


class PromotionLinkCreate(PromotionModel):
    content_name: str = Field(min_length=1, max_length=160)
    channel_id: str = Field(min_length=3, max_length=100)
    campaign_id: str | None = Field(default=None, max_length=100)
    destination_path: str = Field(min_length=1, max_length=500)
    starts_at_ms: int | None = Field(default=None, ge=0)
    ends_at_ms: int | None = Field(default=None, ge=0)

    @field_validator("destination_path")
    @classmethod
    def local_path_only(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//") or "\r" in value or "\n" in value or "://" in value:
            raise ValueError("destinationPath must be a safe internal path")
        return value

    @model_validator(mode="after")
    def valid_period(self):
        if self.starts_at_ms is not None and self.ends_at_ms is not None and self.ends_at_ms <= self.starts_at_ms:
            raise ValueError("endsAtMs must be later than startsAtMs")
        return self


class PromotionLinkUpdate(PromotionLinkCreate):
    status: Literal["active", "inactive"] = "active"
    reason: str = Field(min_length=3, max_length=500)


class PromotionCloneRequest(PromotionModel):
    content_name: str | None = Field(default=None, min_length=1, max_length=160)
    channel_id: str | None = Field(default=None, min_length=3, max_length=100)
    campaign_id: str | None = Field(default=None, max_length=100)
    reason: str = Field(min_length=3, max_length=500)


class PromotionCostCreate(PromotionModel):
    scope_type: Literal["channel", "campaign", "link"]
    scope_id: str = Field(min_length=3, max_length=100)
    cost_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    amount_cents: int = Field(gt=0, le=1_000_000_000)
    currency: Literal["CNY"] = "CNY"
    reason: str = Field(min_length=3, max_length=500)


class PromotionCostReverse(PromotionModel):
    reason: str = Field(min_length=3, max_length=500)


class PromotionQualification(PromotionModel):
    event_id: str = Field(min_length=8, max_length=128)
    visible_ms: int = Field(ge=0, le=3_600_000)
    page_visible: bool


class PromotionClaim(PromotionModel):
    claim_key: str = Field(min_length=8, max_length=128)


class PromotionDownloadEvent(PromotionModel):
    event_id: str = Field(min_length=8, max_length=128)
    artifact: str = Field(min_length=1, max_length=180)
