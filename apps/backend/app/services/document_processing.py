from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from dataclasses import replace
from json import JSONDecodeError
from queue import Empty, Queue
from threading import Lock, Thread
from time import sleep, time
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.commercial_hardening import CommercialHardeningRepository, CommercialJobRecord
from app.ports.document_processing import ProcessingTaskEvent, ProcessingTaskRecord, ProcessingTaskRepository
from app.ports.document_repository import DocumentRecord, DocumentRepository
from app.services.embedding_pipeline import EmbeddingExecutionError, EmbeddingPipelineService
from app.services.document_parser import DocumentParserService, ParserExecutionError
from app.services.material_availability import MaterialAvailabilityValidator
from app.services.commercial_hardening import job_id


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class PipelineProfile:
    parser_profile: str
    chunk_profile: str


class DocumentProcessingService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        document_repository: DocumentRepository,
        task_repository: ProcessingTaskRepository,
        parser_service: DocumentParserService,
        embedding_pipeline: EmbeddingPipelineService,
        material_availability: MaterialAvailabilityValidator | None = None,
        commercial_repository: CommercialHardeningRepository | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.document_repository = document_repository
        self.task_repository = task_repository
        self.parser_service = parser_service
        self.embedding_pipeline = embedding_pipeline
        self.material_availability = material_availability
        self.commercial_repository = commercial_repository
        self.queue: Queue[str] = Queue()
        self._worker_lock = Lock()
        self._worker_started = False
        self.pipeline_profiles = {
            "resume": PipelineProfile(parser_profile="resume-default", chunk_profile="resume-default"),
            "job_description": PipelineProfile(parser_profile="jd-default", chunk_profile="jd-default"),
            "knowledge": PipelineProfile(parser_profile="knowledge-default", chunk_profile="knowledge-default"),
        }

    def submit_document(self, document: DocumentRecord) -> ProcessingTaskRecord:
        self._require_supported_document_kind(document.document_kind)
        now_ms = _now_ms()
        uploaded = ProcessingTaskRecord(
            task_id=f"task-{uuid4().hex}",
            document_id=document.document_id,
            owner_user_id=document.owner_user_id,
            document_kind=document.document_kind,
            current_stage="UPLOADED",
            retry_count=0,
            max_retries=self.settings.document_processing_max_retries,
            parser_provider=self.settings.document_processing_parser_provider,
            embedding_provider=self.settings.document_processing_embedding_provider,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        uploaded = self.task_repository.save_task(uploaded)
        self._record_event(uploaded, event_name="task_created")
        queued = replace(uploaded, current_stage="QUEUED", queued_at_ms=now_ms, updated_at_ms=now_ms)
        queued = self.task_repository.save_task(queued)
        self._record_event(queued, event_name="task_queued")
        self._enqueue_durable_processing_job(document=document, task=queued, now_ms=now_ms)
        self._ensure_worker()
        self.queue.put(queued.task_id)
        return queued

    def retry_task(self, *, task_id: str, user_id: str) -> ProcessingTaskRecord:
        task = self.task_repository.get_task(task_id)
        if task is None:
            raise DomainRequestError("document-processing", "retry-task", "处理任务不存在。", 404)
        if task.owner_user_id != user_id:
            raise DomainRequestError("document-processing", "retry-task", "不能重试其他用户的处理任务。", 403)
        document = self.document_repository.get_by_id(task.document_id)
        if document is None:
            raise DomainRequestError("document-processing", "retry-task", "关联文档不存在。", 404)
        reset = replace(
            task,
            current_stage="QUEUED",
            error_code=None,
            error_message=None,
            queued_at_ms=_now_ms(),
            updated_at_ms=_now_ms(),
            completed_at_ms=None,
            last_retry_at_ms=_now_ms(),
        )
        saved = self.task_repository.save_task(reset)
        self._record_event(saved, event_name="task_requeued_manual")
        self._save_document(document, status="processing_requested", summary="文档已重新进入处理队列，等待后台处理。")
        self._ensure_worker()
        self.queue.put(saved.task_id)
        return saved

    def get_task(self, *, task_id: str, user_id: str) -> ProcessingTaskRecord:
        task = self.task_repository.get_task(task_id)
        if task is None:
            raise DomainRequestError("document-processing", "get-task", "处理任务不存在。", 404)
        if task.owner_user_id != user_id:
            raise DomainRequestError("document-processing", "get-task", "不能查看其他用户的处理任务。", 403)
        return task

    def list_tasks(self, *, user_id: str, document_id: str | None = None) -> list[ProcessingTaskRecord]:
        return self.task_repository.list_tasks_for_user(user_id=user_id, document_id=document_id)

    def list_events(self, *, task_id: str, user_id: str) -> list[ProcessingTaskEvent]:
        task = self.get_task(task_id=task_id, user_id=user_id)
        return self.task_repository.list_events_for_task(task.task_id)

    def latest_task_for_document(self, *, document_id: str, user_id: str) -> ProcessingTaskRecord | None:
        tasks = self.task_repository.list_tasks_for_user(user_id=user_id, document_id=document_id)
        return tasks[0] if tasks else None

    def process_task(self, task_id: str) -> None:
        task = self.task_repository.get_task(task_id)
        if task is None:
            return
        document = self.document_repository.get_by_id(task.document_id)
        if document is None:
            failed = self._fail_task(task, "document_missing", "关联文档不存在。", retryable=False)
            self._record_event(failed, event_name="task_failed", error_code=failed.error_code)
            return
        started_at = _now_ms()
        current_task = task
        try:
            self._save_document(document, status="processing", summary="文档处理中，正在解析内容。")
            current_task = replace(current_task, started_at_ms=started_at, updated_at_ms=started_at)
            current_task, parsed = self.parser_service.parse_document(task=current_task, document=document)
            interview_summary = self._build_interview_summary(document=document, markdown=parsed.markdown)
            if document.document_kind == "knowledge":
                embedding_result = self.embedding_pipeline.process_markdown(task=current_task, document=document, parsed=parsed)
                current_task = embedding_result.task
                chunk_count = embedding_result.chunk_count
            else:
                chunk_count = 0
            if self.material_availability is not None:
                availability = self.material_availability.check_processed_artifacts(document)
                if not availability.available:
                    raise RuntimeError(availability.reason_code or "material_availability_check_failed")
            completed = replace(
                current_task,
                current_stage="COMPLETED",
                chunk_count=chunk_count,
                updated_at_ms=_now_ms(),
                completed_at_ms=_now_ms(),
            )
            completed = self.task_repository.save_task(completed)
            self._record_event(completed, event_name="task_completed", duration_ms=_now_ms() - started_at)
            self._complete_durable_processing_job(task_id=completed.task_id, now_ms=_now_ms(), stage="COMPLETED")
            self._save_document(document, status="ready", summary=interview_summary or f"文档处理完成，已生成 {chunk_count} 个可供 AI 使用的片段。")
        except ParserExecutionError as exc:
            current_task = exc.task
            failed = self._fail_task(
                current_task,
                exc.failure.error_code,
                exc.failure.message_safe_for_log,
                retryable=exc.failure.retryable and current_task.retry_count < current_task.max_retries,
            )
            self._record_event(failed, event_name="task_failed", error_code=failed.error_code)
            if failed.current_stage == "QUEUED":
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "parser_failed", retryable=True)
                sleep(self.settings.document_processing_retry_backoff_ms / 1000)
                self.queue.put(failed.task_id)
            else:
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "parser_failed", retryable=False)
                self._save_document(document, status="failed", summary="文档解析失败，可稍后重试。")
        except EmbeddingExecutionError as exc:
            current_task = exc.task
            failed = self._fail_task(
                current_task,
                exc.failure.error_code,
                exc.failure.message_safe_for_log,
                retryable=exc.failure.retryable and current_task.retry_count < current_task.max_retries,
            )
            self._record_event(failed, event_name="task_failed", error_code=failed.error_code)
            if failed.current_stage == "QUEUED":
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "embedding_failed", retryable=True)
                sleep(self.settings.document_processing_retry_backoff_ms / 1000)
                self.queue.put(failed.task_id)
            else:
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "embedding_failed", retryable=False)
                self._save_document(document, status="failed", summary="文档向量化失败，可稍后重试。")
        except Exception as exc:  # pragma: no cover - exercised through behavior, exception type environment dependent
            failed = self._fail_task(current_task, exc.__class__.__name__, "文档处理失败。", retryable=current_task.retry_count < current_task.max_retries)
            self._record_event(failed, event_name="task_failed", error_code=failed.error_code)
            if failed.current_stage == "QUEUED":
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "processing_failed", retryable=True)
                sleep(self.settings.document_processing_retry_backoff_ms / 1000)
                self.queue.put(failed.task_id)
            else:
                self._fail_durable_processing_job(task_id=failed.task_id, now_ms=_now_ms(), safe_error_code=failed.error_code or "processing_failed", retryable=False)
                self._save_document(document, status="failed", summary="文档处理失败，可稍后重试。")

    def _fail_task(self, task: ProcessingTaskRecord, error_code: str, error_message: str, *, retryable: bool) -> ProcessingTaskRecord:
        now_ms = _now_ms()
        if retryable:
            retried = replace(
                task,
                current_stage="QUEUED",
                retry_count=task.retry_count + 1,
                error_code=error_code,
                error_message=error_message,
                updated_at_ms=now_ms,
                last_retry_at_ms=now_ms,
            )
            retried = self.task_repository.save_task(retried)
            self._record_event(retried, event_name="task_retry_scheduled", error_code=error_code)
            return retried
        failed = replace(
            task,
            current_stage="FAILED",
            retry_count=task.retry_count + 1,
            error_code=error_code,
            error_message=error_message,
            updated_at_ms=now_ms,
            completed_at_ms=now_ms,
        )
        return self.task_repository.save_task(failed)

    def _advance_stage(self, task: ProcessingTaskRecord, stage: str, *, started_at_ms: int | None = None) -> ProcessingTaskRecord:
        updated = replace(
            task,
            current_stage=stage,  # type: ignore[arg-type]
            updated_at_ms=_now_ms(),
            started_at_ms=started_at_ms if started_at_ms is not None else task.started_at_ms,
            error_code=None,
            error_message=None,
        )
        saved = self.task_repository.save_task(updated)
        self._record_event(saved, event_name=f"stage_{stage.lower()}")
        return saved

    def _record_event(self, task: ProcessingTaskRecord, *, event_name: str, duration_ms: int | None = None, error_code: str | None = None) -> None:
        event = ProcessingTaskEvent(
            event_id=f"event-{uuid4().hex}",
            task_id=task.task_id,
            stage=task.current_stage,
            retry_count=task.retry_count,
            event_name=event_name,
            duration_ms=duration_ms,
            error_code=error_code,
            created_at_ms=_now_ms(),
        )
        self.task_repository.save_event(event)
        log_event(
            self.logger,
            logging.INFO if error_code is None else logging.WARNING,
            settings=self.settings,
            event="document_processing.task_event",
            feature="document-processing",
            action=event_name,
            task_id=task.task_id,
            document_id=task.document_id,
            document_kind=task.document_kind,
            current_stage=task.current_stage,
            retry_count=task.retry_count,
            duration_ms=duration_ms,
            error_code=error_code,
        )

    def _enqueue_durable_processing_job(self, *, document: DocumentRecord, task: ProcessingTaskRecord, now_ms: int) -> None:
        if self.commercial_repository is None:
            return
        self.commercial_repository.enqueue_processing_job(
            CommercialJobRecord(
                job_id=job_id("processing"),
                owner_user_id=document.owner_user_id,
                job_kind="processing",
                status="queued",
                stage="QUEUED",
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                related_task_id=task.task_id,
                retry_count=task.retry_count,
                max_retries=task.max_retries,
                payload={
                    "documentKind": document.document_kind,
                    "fileKind": document.file_kind,
                    "parserProvider": task.parser_provider,
                    "embeddingProvider": task.embedding_provider,
                },
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
                scheduled_after_ms=now_ms,
            )
        )

    def _complete_durable_processing_job(self, *, task_id: str, now_ms: int, stage: str) -> None:
        if self.commercial_repository is not None:
            self.commercial_repository.complete_processing_job_for_task(related_task_id=task_id, now_ms=now_ms, stage=stage)

    def _fail_durable_processing_job(self, *, task_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> None:
        if self.commercial_repository is not None:
            self.commercial_repository.fail_processing_job_for_task(
                related_task_id=task_id,
                now_ms=now_ms,
                safe_error_code=safe_error_code,
                retryable=retryable,
            )

    def _save_document(self, document: DocumentRecord, *, status: str, summary: str) -> DocumentRecord:
        index_state = document.index_state
        if status == "processing":
            index_state = "processing"
        elif status == "ready":
            index_state = "indexed"
        elif status == "failed":
            index_state = "failed"
        updated = replace(document, status=status, summary=summary, updated_at_ms=_now_ms(), index_state=index_state)
        return self.document_repository.save(updated)

    def _build_interview_summary(self, *, document: DocumentRecord, markdown: str) -> str | None:
        if document.document_kind not in {"resume", "job_description"}:
            return None
        clean_text = self._compact_markdown(markdown)
        if not clean_text:
            return None
        llm_summary = self._try_remote_interview_summary(document=document, clean_text=clean_text)
        if llm_summary:
            return llm_summary
        return self._extractive_interview_summary(document=document, clean_text=clean_text)

    def _try_remote_interview_summary(self, *, document: DocumentRecord, clean_text: str) -> str | None:
        if not self.settings.chat_qwen_base_url or not self.settings.chat_qwen_api_key:
            return None
        kind_label = "简历" if document.document_kind == "resume" else "职位 JD"
        prompt = (
            f"请把下面{kind_label}压缩成实时面试助手可直接使用的中文资料摘要。"
            "要求：只保留事实，不编造；控制在 500 字以内；用短段落或项目符号；"
            "简历突出候选人背景、项目、技术栈、成果；JD突出岗位职责、硬性要求、加分项。\n\n"
            f"{clean_text[:8000]}"
        )
        payload = {
            "model": self.settings.chat_qwen_model,
            "stream": False,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": "你是面试资料摘要助手，只做事实压缩，不做评价和扩写。"},
                {"role": "user", "content": prompt},
            ],
        }
        base_url = self.settings.chat_qwen_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        started_at = _now_ms()
        try:
            with httpx.Client(timeout=httpx.Timeout(8.0, connect=2.0, read=8.0, write=4.0, pool=2.0)) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {self.settings.chat_qwen_api_key}"}, json=payload)
            if response.status_code >= 400:
                return None
            body = response.json()
            choices = body.get("choices") if isinstance(body, dict) else None
            if not isinstance(choices, list) or not choices:
                return None
            content = choices[0].get("message", {}).get("content")
            if not isinstance(content, str):
                return None
            summary = self._compact_markdown(content)
            if not summary:
                return None
            return f"{kind_label}面试摘要：\n{summary[:900]}"
        except (httpx.HTTPError, JSONDecodeError, KeyError, TypeError, ValueError):
            return None
        finally:
            log_event(
                self.logger,
                logging.INFO,
                settings=self.settings,
                event="document_processing.interview_summary_finished",
                feature="document-processing",
                action="interview-summary",
                document_id=document.document_id,
                document_kind=document.document_kind,
                duration_ms=_now_ms() - started_at,
            )

    def _extractive_interview_summary(self, *, document: DocumentRecord, clean_text: str) -> str:
        kind_label = "简历" if document.document_kind == "resume" else "职位 JD"
        sentences = re.split(r"(?<=[。！？；;])\s+|\n+", clean_text)
        keywords = (
            "项目", "负责", "经验", "算法", "模型", "训练", "推理", "RAG", "Agent", "数据", "工程", "优化", "部署", "指标", "成果",
            "要求", "职责", "任职", "岗位", "能力", "熟悉", "优先", "加分", "本科", "硕士",
        )
        selected: list[str] = []
        for sentence in sentences:
            item = sentence.strip(" -#\t")
            if len(item) < 8:
                continue
            if any(keyword.lower() in item.lower() for keyword in keywords):
                selected.append(item)
            if len(selected) >= 8:
                break
        if not selected:
            selected = [clean_text[:700]]
        summary = "\n".join(f"- {item[:140]}" for item in selected)
        return f"{kind_label}面试摘要：\n{summary[:900]}"

    def _compact_markdown(self, text: str) -> str:
        compact = re.sub(r"`{3}.*?`{3}", " ", text, flags=re.S)
        compact = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", compact)
        compact = re.sub(r"\[[^\]]+]\([^)]*\)", " ", compact)
        compact = re.sub(r"[ \t]+", " ", compact)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        return compact.strip()

    def _require_supported_document_kind(self, document_kind: str) -> PipelineProfile:
        profile = self.pipeline_profiles.get(document_kind)
        if profile is None:
            raise DomainRequestError("document-processing", "submit-document", "当前文档类型还没有注册到处理流水线。", 400)
        return profile

    def _ensure_worker(self) -> None:
        with self._worker_lock:
            if self._worker_started:
                return
            worker = Thread(target=self._worker_loop, name="document-processing-worker", daemon=True)
            worker.start()
            self._worker_started = True

    def _worker_loop(self) -> None:
        while True:
            try:
                task_id = self.queue.get(timeout=0.2)
            except Empty:
                sleep(0.05)
                continue
            try:
                self.process_task(task_id)
            finally:
                self.queue.task_done()
