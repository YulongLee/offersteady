from __future__ import annotations

from dataclasses import dataclass

import psycopg

from app.core.config import Settings


@dataclass(frozen=True)
class DatabaseHealthStatus:
    configured: bool
    healthy: bool
    message: str


class DatabaseRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_health(self) -> DatabaseHealthStatus:
        if not self.settings.database_url:
            return DatabaseHealthStatus(configured=False, healthy=False, message="database_url_not_configured")
        try:
            with psycopg.connect(
                self.settings.database_url,
                connect_timeout=self.settings.database_connect_timeout_seconds,
                application_name=self.settings.database_application_name,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select 1")
                    cursor.fetchone()
            return DatabaseHealthStatus(configured=True, healthy=True, message="ok")
        except Exception as exc:  # pragma: no cover - depends on environment
            return DatabaseHealthStatus(configured=True, healthy=False, message=exc.__class__.__name__)
