from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from time import time
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.commercial_hardening import AiUsageRecord, CommercialHardeningRepository, MaterialArtifactRecord
from app.ports.document_processing import (
    DocumentParserContext,
    DocumentParserPort,
    MarkdownNormalizerPort,
    ParsedDocument,
    ParserFailure,
    ParserStatusPort,
    ParserWarning,
    ProcessingTaskEvent,
    ProcessingTaskRecord,
    ProcessingTaskRepository,
)
from app.ports.document_repository import DocumentRecord
from app.ports.storage import FileStoragePort
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.commercial_hardening import artifact_id, usage_id


def _now_ms() -> int:
    return int(time() * 1000)


class ParserExecutionError(Exception):
    def __init__(self, *, task: ProcessingTaskRecord, failure: ParserFailure):
        self.task = task
        self.failure = failure
        super().__init__(failure.message_safe_for_log)


class DocumentParserService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        object_storage: FileStoragePort,
        binary_parser: DocumentParserPort,
        markdown_normalizer: MarkdownNormalizerPort,
        status_reporter: ParserStatusPort,
        commercial_repository: CommercialHardeningRepository | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.object_storage = object_storage
        self.binary_parser = binary_parser
        self.markdown_normalizer = markdown_normalizer
        self.status_reporter = status_reporter
        self.commercial_repository = commercial_repository

    def parse_document(self, *, task: ProcessingTaskRecord, document: DocumentRecord) -> tuple[ProcessingTaskRecord, ParsedDocument]:
        started_at = _now_ms()
        task = self.status_reporter.mark_parsing_started(task)
        context = DocumentParserContext(
            task_id=task.task_id,
            document_id=document.document_id,
            document_kind=document.document_kind,
            file_kind=document.file_kind,
            content_type=document.content_type,
            object_key=document.object_key,
            display_name=document.display_name,
            retry_count=task.retry_count,
        )
        try:
            if document.object_key.startswith("inline://"):
                parsed = self._parse_inline_document(context=context, document=document)
            elif document.file_kind in {"pdf", "docx", "doc", "txt", "md"}:
                payload = self.object_storage.load_object_bytes(object_key=document.object_key)
                parsed = self.binary_parser.parse(context=context, payload=payload)
            else:
                raise self._failure(
                    task=task,
                    error_code="unsupported_format",
                    error_type="permanent",
                    retryable=False,
                    provider_name="document-parser-service",
                    message_safe_for_log=f"当前文件格式 {document.file_kind} 还没有注册解析能力。",
                )

            normalized = self.markdown_normalizer.normalize(
                markdown=parsed.markdown,
                document_kind=document.document_kind,
                file_kind=document.file_kind,
            )
            if not normalized.markdown.strip():
                raise self._failure(
                    task=task,
                    error_code="empty_document",
                    error_type="permanent",
                    retryable=False,
                    provider_name=parsed.provider_name,
                    message_safe_for_log="文本内容为空，无法建立解析结果。",
                )
            if document.document_version_id:
                normalized_key = MaterialObjectKeyFactory(self.settings).processed_artifact_key(
                    owner_user_id=document.owner_user_id,
                    document_kind=document.document_kind,
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    artifact_kind="normalized_markdown",
                )
                self.object_storage.save_object_bytes(
                    object_key=normalized_key,
                    payload=normalized.markdown.encode("utf-8"),
                    content_type="text/markdown; charset=utf-8",
                )
                self._record_normalized_artifact(document=document, object_key=normalized_key, size_bytes=len(normalized.markdown.encode("utf-8")))
            parsed = replace(parsed, markdown=normalized.markdown)
            task = self.status_reporter.mark_parsing_succeeded(task, parsed, duration_ms=_now_ms() - started_at)
            self._record_parser_usage(task=task, document=document, provider=parsed.provider_name, status="succeeded", duration_ms=_now_ms() - started_at)
            return task, parsed
        except ParserExecutionError as exc:
            failed_task = self.status_reporter.mark_parsing_failed(exc.task, exc.failure, duration_ms=_now_ms() - started_at)
            self._record_parser_usage(task=failed_task, document=document, provider=exc.failure.provider_name, status="failed", duration_ms=_now_ms() - started_at, safe_error_code=exc.failure.error_code)
            raise ParserExecutionError(task=failed_task, failure=exc.failure) from exc
        except UnicodeDecodeError as exc:
            failure = ParserFailure(
                error_code="text_decode_failed",
                error_type="permanent",
                retryable=False,
                provider_name="text-parser",
                message_safe_for_log="文本文件解码失败，当前仅支持 UTF-8 编码文本。",
            )
            failed_task = self.status_reporter.mark_parsing_failed(task, failure, duration_ms=_now_ms() - started_at)
            self._record_parser_usage(task=failed_task, document=document, provider=failure.provider_name, status="failed", duration_ms=_now_ms() - started_at, safe_error_code=failure.error_code)
            raise ParserExecutionError(task=failed_task, failure=failure) from exc
        except DomainRequestError as exc:
            failure = ParserFailure(
                error_code="object_load_failed",
                error_type="recoverable",
                retryable=True,
                provider_name="object-storage",
                message_safe_for_log=exc.message,
            )
            failed_task = self.status_reporter.mark_parsing_failed(task, failure, duration_ms=_now_ms() - started_at)
            self._record_parser_usage(task=failed_task, document=document, provider=failure.provider_name, status="failed", duration_ms=_now_ms() - started_at, safe_error_code=failure.error_code)
            raise ParserExecutionError(task=failed_task, failure=failure) from exc
        except Exception as exc:
            safe_message = "文档解析阶段出现未预期错误。"
            if exc.__class__.__name__ == "RuntimeError" and str(exc).startswith("MinerU parsing failed"):
                safe_message = str(exc)
            failure = ParserFailure(
                error_code="parser_unexpected_error",
                error_type="recoverable",
                retryable=True,
                provider_name="document-parser-service",
                message_safe_for_log=safe_message,
            )
            failed_task = self.status_reporter.mark_parsing_failed(task, failure, duration_ms=_now_ms() - started_at)
            self._record_parser_usage(task=failed_task, document=document, provider=failure.provider_name, status="failed", duration_ms=_now_ms() - started_at, safe_error_code=failure.error_code)
            raise ParserExecutionError(task=failed_task, failure=failure) from exc

    def _record_normalized_artifact(self, *, document: DocumentRecord, object_key: str, size_bytes: int) -> None:
        if self.commercial_repository is None or not document.document_version_id:
            return
        now = _now_ms()
        self.commercial_repository.save_artifact(
            MaterialArtifactRecord(
                artifact_id=artifact_id(),
                owner_user_id=document.owner_user_id,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                document_kind=document.document_kind,
                artifact_kind="normalized_markdown",
                object_key=object_key,
                sync_status="synced",
                required=True,
                content_type="text/markdown; charset=utf-8",
                size_bytes=size_bytes,
                verified_at_ms=now,
                created_at_ms=now,
                updated_at_ms=now,
            )
        )

    def _record_parser_usage(
        self,
        *,
        task: ProcessingTaskRecord,
        document: DocumentRecord,
        provider: str,
        status: str,
        duration_ms: int,
        safe_error_code: str | None = None,
    ) -> None:
        if self.commercial_repository is None:
            return
        self.commercial_repository.record_ai_usage(
            AiUsageRecord(
                usage_id=usage_id(),
                owner_user_id=document.owner_user_id,
                operation_kind="parser",
                provider=provider,
                model=provider,
                status=status,  # type: ignore[arg-type]
                related_task_id=task.task_id,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                input_units=document.size_bytes,
                duration_ms=duration_ms,
                safe_error_code=safe_error_code,
                created_at_ms=_now_ms(),
            )
        )

    def _parse_text_document(self, *, task: ProcessingTaskRecord, context: DocumentParserContext) -> ParsedDocument:
        payload = self.object_storage.load_object_bytes(object_key=context.object_key)
        text = payload.decode("utf-8").strip()
        if not text:
            raise self._failure(
                task=task,
                error_code="empty_document",
                error_type="permanent",
                retryable=False,
                provider_name="text-parser",
                message_safe_for_log="文本内容为空，无法建立解析结果。",
            )
        title = Path(context.display_name).stem or text.splitlines()[0][:32]
        warnings: list[ParserWarning] = []
        if context.file_kind == "md":
            markdown = text
        else:
            markdown = f"# {title}\n\n{text}\n"
            warnings.append(ParserWarning(code="text_wrapped_as_markdown", message="纯文本内容已包装为标准 Markdown。"))
        return ParsedDocument(
            markdown=markdown,
            provider_name="text-parser",
            detected_title=title,
            warnings=warnings,
            metadata={"parserProfile": "plain-text", "fileKind": context.file_kind},
        )

    def _parse_inline_document(self, *, context: DocumentParserContext, document: DocumentRecord) -> ParsedDocument:
        title = Path(document.display_name).stem or "Inline JD"
        markdown = (
            f"# {title}\n\n"
            f"- document kind: {document.document_kind}\n"
            f"- source key: `{document.object_key}`\n\n"
            "当前为内联文本占位解析结果；后续接入真实持久化后可替换为原始文本解析。"
        )
        return ParsedDocument(
            markdown=markdown,
            provider_name="inline-text",
            detected_title=title,
            warnings=[ParserWarning(code="inline_placeholder", message="当前使用内联文本占位解析结果。")],
            metadata={"parserProfile": "inline-text"},
        )

    def _failure(
        self,
        *,
        task: ProcessingTaskRecord | None,
        error_code: str,
        error_type: str,
        retryable: bool,
        provider_name: str,
        message_safe_for_log: str,
    ) -> ParserExecutionError:
        failure = ParserFailure(
            error_code=error_code,
            error_type=error_type,  # type: ignore[arg-type]
            retryable=retryable,
            provider_name=provider_name,
            message_safe_for_log=message_safe_for_log,
        )
        if task is None:
            raise RuntimeError("Parser failure helper requires a bound processing task.")
        return ParserExecutionError(task=task, failure=failure)


class ProcessingTaskParserStatusReporter(ParserStatusPort):
    def __init__(self, *, settings: Settings, logger: logging.Logger, task_repository: ProcessingTaskRepository) -> None:
        self.settings = settings
        self.logger = logger
        self.task_repository = task_repository

    def mark_parsing_started(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord:
        started = replace(
            task,
            current_stage="PARSING",
            started_at_ms=task.started_at_ms or _now_ms(),
            updated_at_ms=_now_ms(),
            error_code=None,
            error_message=None,
        )
        saved = self.task_repository.save_task(started)
        self._record(saved, action="parser_started")
        return saved

    def mark_parsing_succeeded(self, task: ProcessingTaskRecord, parsed: ParsedDocument, *, duration_ms: int) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(
            replace(
                task,
                parser_provider=parsed.provider_name,
                updated_at_ms=_now_ms(),
                error_code=None,
                error_message=None,
            )
        )
        self._record(saved, action="parser_succeeded", duration_ms=duration_ms)
        return saved

    def mark_parsing_failed(self, task: ProcessingTaskRecord, failure: ParserFailure, *, duration_ms: int) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(
            replace(
                task,
                current_stage="PARSING",
                parser_provider=failure.provider_name,
                updated_at_ms=_now_ms(),
                error_code=failure.error_code,
                error_message=failure.message_safe_for_log,
            )
        )
        self._record(saved, action="parser_failed", duration_ms=duration_ms, error_code=failure.error_code)
        return saved

    def _record(self, task: ProcessingTaskRecord, *, action: str, duration_ms: int | None = None, error_code: str | None = None) -> None:
        self.task_repository.save_event(
            ProcessingTaskEvent(
                event_id=f"event-{uuid4().hex}",
                task_id=task.task_id,
                stage=task.current_stage,
                retry_count=task.retry_count,
                event_name=action,
                duration_ms=duration_ms,
                error_code=error_code,
                created_at_ms=_now_ms(),
            )
        )
        log_event(
            self.logger,
            logging.INFO if error_code is None else logging.WARNING,
            settings=self.settings,
            event="document_parser.task_event",
            feature="document-parser",
            action=action,
            task_id=task.task_id,
            document_id=task.document_id,
            document_kind=task.document_kind,
            parser_provider=task.parser_provider,
            current_stage=task.current_stage,
            retry_count=task.retry_count,
            duration_ms=duration_ms,
            error_code=error_code,
        )
