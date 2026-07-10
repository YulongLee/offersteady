from __future__ import annotations

import hashlib
import io
import math
import os
import zipfile
from pathlib import Path
from time import sleep
from typing import Any

import httpx

from app.core.config import Settings
from app.material_formats import MaterialKind
from app.ports.document_processing import (
    ChunkMetadataBuilderPort,
    ChunkRecord,
    ChunkSplitterPort,
    ChunkingProfile,
    CleanedMarkdown,
    DocumentParserContext,
    DocumentParserPort,
    EmbeddedChunk,
    EmbeddingPort,
    MarkdownCleanerPort,
    MarkdownNormalizerPort,
    NormalizedDocument,
    ParsedDocument,
    ParserWarning,
    StoredVectorRecord,
    VectorStorePort,
)


class MineruDocumentParserAdapter(DocumentParserPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def parse(self, *, context: DocumentParserContext, payload: bytes) -> ParsedDocument:
        if context.file_kind in {"txt", "md"}:
            return self._parse_text_payload(context=context, payload=payload)
        should_use_remote_mineru = self.settings.integration_mineru_base_url and (
            not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_MINERU") == "1"
        )
        if should_use_remote_mineru:
            try:
                return self._parse_with_mineru(context=context, payload=payload)
            except Exception as exc:
                raise RuntimeError(f"MinerU parsing failed with {exc.__class__.__name__}") from exc
        return self._parse_placeholder(context=context, payload=payload)

    def _parse_with_mineru(self, *, context: DocumentParserContext, payload: bytes) -> ParsedDocument:
        url = self._mineru_url()
        source_url = self._signed_oss_url(context.object_key)
        request_payload: dict[str, Any] = {
            "model_version": "vlm",
            "filename": context.display_name,
            "content_type": context.content_type,
            "enable_formula": True,
            "enable_table": True,
        }
        if source_url:
            request_payload["url"] = source_url
        else:
            request_payload["content_base64"] = payload.hex()
            request_payload["content_encoding"] = "hex"
        headers = {"Content-Type": "application/json"}
        if self.settings.integration_mineru_api_key:
            headers["Authorization"] = f"Bearer {self.settings.integration_mineru_api_key}"
        with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=request_payload)
        if response.status_code >= 400:
            response.raise_for_status()
        response_payload = response.json()
        markdown = self._extract_markdown(response_payload)
        if not markdown.strip():
            task_id = self._extract_task_id(response_payload)
            if task_id:
                markdown = self._poll_mineru_markdown(task_id=task_id, headers=headers)
        if not markdown.strip():
            raise ValueError("MinerU response does not include Markdown content.")
        title = Path(context.display_name).stem or {"resume": "Resume", "job_description": "JD", "knowledge": "Knowledge Base"}[context.document_kind]
        return ParsedDocument(
            markdown=markdown,
            provider_name=self.settings.document_processing_parser_provider,
            detected_title=title,
            metadata={"parserProfile": "mineru", "fileKind": context.file_kind},
        )

    def _mineru_url(self) -> str:
        base = (self.settings.integration_mineru_base_url or "").rstrip("/")
        if base.endswith("/api/v4"):
            return f"{base}/extract/task"
        if base.endswith("/extract/task"):
            return base
        path = self.settings.integration_mineru_parse_path
        return f"{base}{path if path.startswith('/') else f'/{path}'}"

    def _mineru_result_url(self, task_id: str) -> str:
        base = (self.settings.integration_mineru_base_url or "").rstrip("/")
        if base.endswith("/extract/task"):
            return f"{base}/{task_id}"
        if base.endswith("/api/v4"):
            return f"{base}/extract/task/{task_id}"
        path = self.settings.integration_mineru_result_path.format(task_id=task_id)
        if path.startswith(("http://", "https://")):
            return path
        return f"{base}{path if path.startswith('/') else f'/{path}'}"

    def _signed_oss_url(self, object_key: str) -> str | None:
        if not (
            self.settings.oss_access_key_id
            and self.settings.oss_access_key_secret
            and self.settings.oss_bucket
            and self.settings.oss_endpoint
        ):
            return None
        try:
            from oss2 import Auth, Bucket
        except ImportError:
            return None
        endpoint = self.settings.oss_endpoint.strip()
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"https://{endpoint}"
        auth = Auth(self.settings.oss_access_key_id, self.settings.oss_access_key_secret)
        bucket = Bucket(auth, endpoint, self.settings.oss_bucket)
        return bucket.sign_url("GET", object_key, self.settings.oss_upload_intent_ttl_seconds)

    def _poll_mineru_markdown(self, *, task_id: str, headers: dict[str, str]) -> str:
        result_url = self._mineru_result_url(task_id)
        attempts = max(1, self.settings.integration_mineru_poll_attempts)
        interval_seconds = max(0, self.settings.integration_mineru_poll_interval_ms) / 1000
        with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
            for attempt in range(attempts):
                response = client.get(result_url, headers={key: value for key, value in headers.items() if key.lower() != "content-type"})
                if response.status_code in {202, 204, 404}:
                    if attempt < attempts - 1 and interval_seconds:
                        sleep(interval_seconds)
                    continue
                if response.status_code >= 400:
                    response.raise_for_status()
                payload = response.json()
                status = str(self._extract_by_path(payload, self.settings.integration_mineru_status_field) or "").lower()
                if not status:
                    status = str(self._extract_by_path(payload, "data.status") or "").lower()
                if status in {"failed", "failure", "error"}:
                    message = self._extract_by_path(payload, "data.err_msg") or self._extract_by_path(payload, "msg") or "MinerU parsing task failed."
                    raise ValueError(str(message))
                markdown = self._extract_markdown(payload)
                if markdown.strip():
                    return markdown
                zip_url = self._extract_zip_url(payload)
                if zip_url:
                    markdown = self._download_markdown_from_zip(zip_url=zip_url)
                    if markdown.strip():
                        return markdown
                if status in {"done", "completed", "success"}:
                    raise ValueError("MinerU parsing task completed without full.md.")
                if attempt < attempts - 1 and interval_seconds:
                    sleep(interval_seconds)
        return ""

    def _extract_markdown(self, payload: dict[str, Any]) -> str:
        value = self._extract_by_path(payload, self.settings.integration_mineru_markdown_field)
        if isinstance(value, str):
            return value
        for key in ("markdown", "md", "content"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("markdown", "md", "content"):
                value = data.get(key)
                if isinstance(value, str):
                    return value
        return ""

    def _extract_zip_url(self, payload: dict[str, Any]) -> str:
        for path in ("data.full_zip_url", "data.zip_url", "full_zip_url", "zip_url"):
            value = self._extract_by_path(payload, path)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _download_markdown_from_zip(self, *, zip_url: str) -> str:
        with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
            response = client.get(zip_url)
        if response.status_code >= 400:
            response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
            preferred = next((name for name in names if name.endswith("/full.md") or name == "full.md"), "")
            if not preferred:
                preferred = next((name for name in names if name.endswith(".md")), "")
            if not preferred:
                return ""
            return archive.read(preferred).decode("utf-8", errors="replace")

    def _extract_task_id(self, payload: dict[str, Any]) -> str:
        value = self._extract_by_path(payload, self.settings.integration_mineru_task_id_field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        for key in ("task_id", "taskId", "id", "extract_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("task_id", "taskId", "id", "extract_id"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    def _extract_by_path(self, payload: dict[str, Any], path: str) -> Any:
        value: Any = payload
        for segment in path.split("."):
            if isinstance(value, dict):
                value = value.get(segment)
            else:
                return None
        return value

    def _parse_text_payload(self, *, context: DocumentParserContext, payload: bytes) -> ParsedDocument:
        text = payload.decode("utf-8").strip()
        if not text:
            return ParsedDocument(
                markdown="",
                provider_name="text-parser",
                detected_title=Path(context.display_name).stem,
                metadata={"parserProfile": "plain-text", "fileKind": context.file_kind},
            )
        title = Path(context.display_name).stem or text.splitlines()[0][:32] if text else Path(context.display_name).stem
        markdown = text if context.file_kind == "md" else f"# {title}\n\n{text}\n"
        return ParsedDocument(
            markdown=markdown,
            provider_name="text-parser",
            detected_title=title,
            warnings=[],
            metadata={"parserProfile": "plain-text", "fileKind": context.file_kind},
        )

    def _parse_placeholder(self, *, context: DocumentParserContext, payload: bytes) -> ParsedDocument:
        title = Path(context.display_name).stem or {"resume": "Resume", "job_description": "JD", "knowledge": "Knowledge Base"}[context.document_kind]
        warnings = [ParserWarning(code="mineru_placeholder", message="当前使用 MVP 占位 MinerU 适配器，尚未接入真实解析服务。")]
        markdown = (
            f"# {title}\n\n"
            f"- document kind: {context.document_kind}\n"
            f"- file kind: {context.file_kind}\n"
            f"- source key: `{context.object_key}`\n"
            f"- payload size: {len(payload)} bytes\n\n"
            "解析内容已进入统一 Parser Service，占位解析结果用于验证处理架构与 Markdown 标准化链路。"
        )
        return ParsedDocument(
            markdown=markdown,
            provider_name=self.settings.document_processing_parser_provider,
            detected_title=title,
            warnings=warnings,
            metadata={"parserProfile": "mineru-binary", "fileKind": context.file_kind},
        )


class MarkdownNormalizerAdapter(MarkdownNormalizerPort):
    def normalize(self, *, markdown: str, document_kind: MaterialKind, file_kind: str) -> NormalizedDocument:
        normalized = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
        normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
        while "\n\n\n" in normalized:
            normalized = normalized.replace("\n\n\n", "\n\n")
        if not normalized.endswith("\n"):
            normalized += "\n"
        return NormalizedDocument(markdown=normalized)


class MarkdownCleanerAdapter(MarkdownCleanerPort):
    def clean(self, *, markdown: str, document_kind: MaterialKind) -> CleanedMarkdown:
        cleaned = markdown.replace("\t", "  ").strip()
        cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        return CleanedMarkdown(markdown=cleaned, metadata={"cleaner": "markdown-cleaner-v1", "documentKind": document_kind})


class MarkdownChunkSplitterAdapter(ChunkSplitterPort):
    def split(self, *, markdown: str, document_kind: MaterialKind, profile: ChunkingProfile) -> list[ChunkRecord]:
        chunk_size = max(64, profile.chunk_size)
        overlap = max(0, min(profile.overlap, chunk_size // 2))
        text = markdown.strip()
        if not text:
            return []
        chunks: list[ChunkRecord] = []
        start = 0
        index = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            content = text[start:end]
            chunks.append(ChunkRecord(
                chunk_id=f"chunk-{index}",
                content=content,
                index=index,
                metadata={"documentKind": document_kind, "chunkProfile": profile.profile_name},
            ))
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
            index += 1
        return chunks


class ChunkMetadataBuilderAdapter(ChunkMetadataBuilderPort):
    def build(
        self,
        *,
        document_id: str,
        document_kind: MaterialKind,
        profile: ChunkingProfile,
        parser_metadata: dict[str, str],
        chunks: list[ChunkRecord],
        rebuild_version: int,
    ) -> list[ChunkRecord]:
        built: list[ChunkRecord] = []
        for chunk in chunks:
            metadata = {
                **chunk.metadata,
                **parser_metadata,
                "documentId": document_id,
                "documentKind": document_kind,
                "chunkIndex": str(chunk.index),
                "chunkProfile": profile.profile_name,
                "rebuildVersion": str(rebuild_version),
            }
            built.append(ChunkRecord(chunk_id=chunk.chunk_id, content=chunk.content, index=chunk.index, metadata=metadata))
        return built


class SyntheticEmbeddingAdapter(EmbeddingPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed(self, *, chunks: list[ChunkRecord], document_kind: MaterialKind, embedding_model: str, batch_size: int) -> list[EmbeddedChunk]:
        embedded: list[EmbeddedChunk] = []
        effective_batch_size = max(1, batch_size)
        for start in range(0, len(chunks), effective_batch_size):
            batch = chunks[start:start + effective_batch_size]
            for chunk in batch:
                digest = hashlib.sha256(f"{document_kind}:{embedding_model}:{chunk.content}".encode("utf-8")).digest()
                vector = [round(byte / 255, 6) for byte in digest[:8]]
                embedded.append(EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                    content=chunk.content,
                    index=chunk.index,
                    metadata={**chunk.metadata, "embeddingModel": embedding_model},
                ))
        return embedded


class DashScopeCompatibleEmbeddingAdapter(EmbeddingPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed(self, *, chunks: list[ChunkRecord], document_kind: MaterialKind, embedding_model: str, batch_size: int) -> list[EmbeddedChunk]:
        if not chunks:
            return []
        base_url = (self.settings.embedding_base_url or "").rstrip("/")
        api_key = self.settings.embedding_api_key
        if not base_url or not api_key:
            raise RuntimeError("embedding_config_missing")
        model = self.settings.embedding_model or embedding_model
        embedded: list[EmbeddedChunk] = []
        effective_batch_size = max(1, batch_size)
        for start in range(0, len(chunks), effective_batch_size):
            batch = chunks[start:start + effective_batch_size]
            vectors = self._embed_batch(base_url=base_url, api_key=api_key, model=model, inputs=[chunk.content for chunk in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("embedding_provider_invalid_response")
            for chunk, vector in zip(batch, vectors, strict=True):
                embedded.append(EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                    content=chunk.content,
                    index=chunk.index,
                    metadata={**chunk.metadata, "embeddingModel": model},
                ))
        return embedded

    def _embed_batch(self, *, base_url: str, api_key: str, model: str, inputs: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "input": inputs},
            )
        if response.status_code >= 400:
            response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError("embedding_provider_invalid_response")
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0)
        vectors: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(vector, list):
                raise RuntimeError("embedding_provider_invalid_response")
            vectors.append([float(value) for value in vector])
        return vectors


class InMemoryPgvectorStore(VectorStorePort):
    def __init__(self) -> None:
        self.rows: dict[str, list[StoredVectorRecord]] = {}
        self.chunk_payloads: dict[str, list[EmbeddedChunk]] = {}

    def upsert_document_chunks(
        self,
        *,
        document_id: str,
        document_kind: MaterialKind,
        chunks: list[EmbeddedChunk],
        embedding_model: str,
        rebuild_version: int,
    ) -> int:
        self.rows[document_id] = [
            StoredVectorRecord(
                document_id=document_id,
                document_kind=document_kind,
                chunk_id=chunk.chunk_id,
                embedding_model=embedding_model,
                rebuild_version=rebuild_version,
                chunk_index=chunk.index,
                owner_user_id=chunk.metadata.get("ownerUserId") or None,
                document_version_id=chunk.metadata.get("documentVersionId") or None,
                knowledge_collection_id=chunk.metadata.get("knowledgeCollectionId") or None,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]
        self.chunk_payloads[document_id] = list(chunks)
        return len(chunks)

    def next_rebuild_version(self, *, document_id: str) -> int:
        rows = self.rows.get(document_id, [])
        if not rows:
            return 1
        return max(row.rebuild_version for row in rows) + 1

    def search_similar(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        document_kinds: list[MaterialKind] | None = None,
        document_ids: list[str] | None = None,
        knowledge_collection_ids: list[str] | None = None,
    ):
        from app.ports.document_processing import VectorSearchMatch

        allowed_kinds = set(document_kinds or [])
        allowed_document_ids = set(document_ids or [])
        allowed_collections = set(knowledge_collection_ids or [])
        matches: list[VectorSearchMatch] = []
        for document_id, records in self.rows.items():
            if allowed_document_ids and document_id not in allowed_document_ids:
                continue
            payloads = {chunk.chunk_id: chunk for chunk in self.chunk_payloads.get(document_id, [])}
            for record in records:
                if allowed_kinds and record.document_kind not in allowed_kinds:
                    continue
                collection_id = record.knowledge_collection_id or record.metadata.get("knowledgeCollectionId")
                if allowed_collections and collection_id not in allowed_collections:
                    continue
                payload = payloads.get(record.chunk_id)
                if payload is None:
                    continue
                score = self._cosine_similarity(query_vector, payload.vector)
                matches.append(
                    VectorSearchMatch(
                        document_id=record.document_id,
                        document_kind=record.document_kind,
                        chunk_id=record.chunk_id,
                        chunk_index=record.chunk_index,
                        content=payload.content,
                        score=score,
                        embedding_model=record.embedding_model,
                        rebuild_version=record.rebuild_version,
                        metadata=record.metadata,
                    )
                )
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[: max(1, top_k)]

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        numerator = sum(left[index] * right[index] for index in range(size))
        left_norm = math.sqrt(sum(value * value for value in left[:size]))
        right_norm = math.sqrt(sum(value * value for value in right[:size]))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
