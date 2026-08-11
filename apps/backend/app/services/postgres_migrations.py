from __future__ import annotations

import hashlib
from pathlib import Path
from time import time
from typing import Iterable


MIGRATION_LOCK_NAME = "offersteady:schema-migrations"


def apply_sql_migrations(cursor, migrations: Iterable[Path]) -> None:
    """Apply each SQL migration once under one cross-process transaction lock."""
    cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (MIGRATION_LOCK_NAME,))
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS offersteady_schema_migrations (
          migration_name TEXT PRIMARY KEY,
          content_sha256 TEXT NOT NULL,
          applied_at_ms BIGINT NOT NULL
        )
        """
    )
    for migration in migrations:
        migration_name = migration.name
        content = migration.read_text(encoding="utf8")
        checksum = hashlib.sha256(content.encode("utf8")).hexdigest()
        cursor.execute(
            "SELECT content_sha256 FROM offersteady_schema_migrations WHERE migration_name = %s",
            (migration_name,),
        )
        existing = cursor.fetchone()
        if existing is not None:
            stored_checksum = existing[0] if not isinstance(existing, dict) else existing["content_sha256"]
            if str(stored_checksum) != checksum:
                raise RuntimeError(f"migration_checksum_mismatch:{migration_name}")
            continue
        cursor.execute(content)
        cursor.execute(
            "INSERT INTO offersteady_schema_migrations (migration_name, content_sha256, applied_at_ms) VALUES (%s,%s,%s)",
            (migration_name, checksum, int(time() * 1000)),
        )
