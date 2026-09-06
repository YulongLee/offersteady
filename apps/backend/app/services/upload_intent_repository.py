from __future__ import annotations

from dataclasses import replace
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.ports.storage import UploadIntentRepository, UploadIntentReservation


class InMemoryUploadIntentRepository(UploadIntentRepository):
    def __init__(self) -> None:
        self.reservations: dict[str, UploadIntentReservation] = {}

    def save(self, reservation: UploadIntentReservation) -> UploadIntentReservation:
        stored = replace(reservation)
        self.reservations[stored.intent_id] = stored
        return replace(stored)

    def get(self, intent_id: str) -> UploadIntentReservation | None:
        reservation = self.reservations.get(intent_id)
        return replace(reservation) if reservation else None


class PostgresUploadIntentRepository(UploadIntentRepository):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_table()

    def save(self, reservation: UploadIntentReservation) -> UploadIntentReservation:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO material_upload_intent_reservations (
                      intent_id, owner_user_id, material_kind, filename, file_kind,
                      content_type, object_key, upload_url, upload_fields_json,
                      issued_at_ms, expires_at_ms, object_id, document_id,
                      document_version_id, upload_method
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (intent_id) DO UPDATE SET
                      upload_fields_json = EXCLUDED.upload_fields_json,
                      expires_at_ms = EXCLUDED.expires_at_ms
                    """,
                    (
                        reservation.intent_id,
                        reservation.user_id,
                        reservation.material_kind,
                        reservation.filename,
                        reservation.file_kind,
                        reservation.content_type,
                        reservation.object_key,
                        reservation.upload_url,
                        Jsonb(reservation.upload_fields),
                        reservation.issued_at_ms,
                        reservation.expires_at_ms,
                        reservation.object_id,
                        reservation.document_id,
                        reservation.document_version_id,
                        reservation.upload_method,
                    ),
                )
                cursor.execute(
                    "DELETE FROM material_upload_intent_reservations WHERE expires_at_ms < %s",
                    (reservation.issued_at_ms - 24 * 60 * 60 * 1000,),
                )
            connection.commit()
        return reservation

    def get(self, intent_id: str) -> UploadIntentReservation | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM material_upload_intent_reservations WHERE intent_id = %s", (intent_id,))
            row = cursor.fetchone()
        return self._from_row(row) if row else None

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-upload-intents",
        )

    def _ensure_table(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS material_upload_intent_reservations (
                      intent_id TEXT PRIMARY KEY,
                      owner_user_id TEXT NOT NULL,
                      material_kind TEXT NOT NULL,
                      filename TEXT NOT NULL,
                      file_kind TEXT NOT NULL,
                      content_type TEXT NOT NULL,
                      object_key TEXT NOT NULL,
                      upload_url TEXT NOT NULL,
                      upload_fields_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                      issued_at_ms BIGINT NOT NULL,
                      expires_at_ms BIGINT NOT NULL,
                      object_id TEXT NULL,
                      document_id TEXT NULL,
                      document_version_id TEXT NULL,
                      upload_method TEXT NOT NULL DEFAULT 'POST'
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_material_upload_intent_reservations_expiry ON material_upload_intent_reservations(expires_at_ms)"
                )
            connection.commit()

    @staticmethod
    def _from_row(row: dict[str, Any]) -> UploadIntentReservation:
        return UploadIntentReservation(
            intent_id=row["intent_id"],
            user_id=row["owner_user_id"],
            material_kind=row["material_kind"],
            filename=row["filename"],
            file_kind=row["file_kind"],
            content_type=row["content_type"],
            object_key=row["object_key"],
            upload_url=row["upload_url"],
            upload_fields=dict(row["upload_fields_json"] or {}),
            issued_at_ms=int(row["issued_at_ms"]),
            expires_at_ms=int(row["expires_at_ms"]),
            object_id=row["object_id"],
            document_id=row["document_id"],
            document_version_id=row["document_version_id"],
            upload_method=row["upload_method"],
        )
