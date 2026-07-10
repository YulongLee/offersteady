from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class ObjectStorageHealthStatus:
    configured: bool
    healthy: bool
    message: str


class ObjectStorageRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_health(self) -> ObjectStorageHealthStatus:
        configured = all(
            [
                self.settings.oss_bucket,
                self.settings.oss_endpoint,
                self.settings.oss_region,
                self.settings.oss_access_key_id,
                self.settings.oss_access_key_secret,
            ]
        )
        if not configured:
            return ObjectStorageHealthStatus(configured=False, healthy=False, message="oss_settings_incomplete")
        return ObjectStorageHealthStatus(configured=True, healthy=True, message="configured")
