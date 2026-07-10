from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict


MaterialFormatId = Literal["pdf", "docx", "doc", "txt", "md"]
MaterialKind = Literal["resume", "job_description", "knowledge"]


class MaterialFormatDefinition(TypedDict):
    id: MaterialFormatId
    label: str
    extensions: list[str]
    mimeTypes: list[str]


def _formats_path() -> Path:
    return Path(__file__).resolve().parents[3] / "packages" / "protocol" / "src" / "material-upload-formats.json"


@lru_cache(maxsize=1)
def material_upload_formats() -> tuple[MaterialFormatDefinition, ...]:
    with _formats_path().open("r", encoding="utf-8") as handle:
      loaded = json.load(handle)
    return tuple(loaded)


def material_upload_accept() -> str:
    return ",".join(extension for item in material_upload_formats() for extension in item["extensions"])


def material_upload_label() -> str:
    return "、".join(item["label"] for item in material_upload_formats())


def material_upload_max_file_size_bytes() -> int:
    return 20 * 1024 * 1024


def detect_material_format(filename: str) -> MaterialFormatId | None:
    lowered = filename.lower()
    for item in material_upload_formats():
        if any(lowered.endswith(extension) for extension in item["extensions"]):
            return item["id"]
    return None


def is_material_mime_allowed(format_id: MaterialFormatId, content_type: str) -> bool:
    if not content_type.strip():
        return True
    lowered = content_type.lower()
    return any(item["id"] == format_id and lowered in item["mimeTypes"] for item in material_upload_formats())
