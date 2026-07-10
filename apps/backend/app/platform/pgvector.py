from __future__ import annotations

from dataclasses import dataclass

import psycopg

from app.core.config import Settings


@dataclass(frozen=True)
class PgvectorHealthStatus:
    configured: bool
    extension_available: bool
    message: str


class PgvectorRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_extension(self) -> PgvectorHealthStatus:
        if not self.settings.database_url:
            return PgvectorHealthStatus(configured=False, extension_available=False, message="database_url_not_configured")
        try:
            with psycopg.connect(
                self.settings.database_url,
                connect_timeout=self.settings.database_connect_timeout_seconds,
                application_name=f"{self.settings.database_application_name}-pgvector",
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select extname from pg_extension where extname = %s", (self.settings.pgvector_extension_name,))
                    row = cursor.fetchone()
            if row:
                return PgvectorHealthStatus(configured=True, extension_available=True, message="ok")
            return PgvectorHealthStatus(configured=True, extension_available=False, message="extension_not_installed")
        except Exception as exc:  # pragma: no cover - depends on environment
            return PgvectorHealthStatus(configured=True, extension_available=False, message=exc.__class__.__name__)
