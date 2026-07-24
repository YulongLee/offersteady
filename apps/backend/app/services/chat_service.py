from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Iterator
from dataclasses import replace
from json import JSONDecodeError
from pathlib import Path
from time import time
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.chat import (
    ChatAnswerChunk,
    ChatAnswerTaskRecord,
    ChatRepository,
    GatewayAnswerResult,
    LLMGatewayPort,
    MaterialContextAssembly,
    MaterialContextSource,
    PromptBuildResult,
    PromptBuilderPort,
    PromptConfig,
    PromptTemplatePort,
    UsageReport,
)
from app.ports.retrieval import RetrievalContext, RetrievalFilter, RetrievalPort
from app.ports.storage import FileStoragePort
from app.schemas.retrieval import RetrievalResponse, RetrievedChunkResponse
from app.services.session_service import SessionService


def _now_ms() -> int:
    return int(time() * 1000)


class RetryableChatError(Exception):
    def __init__(self, message: str, *, code: str = "chat_provider_unavailable") -> None:
        self.code = code
        super().__init__(message)


class NonRetryableChatError(Exception):
    def __init__(self, message: str, *, code: str = "chat_provider_invalid_response") -> None:
        self.code = code
        super().__init__(message)


class FilePromptTemplateAdapter(PromptTemplatePort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load_system_prompt(self) -> tuple[str, PromptConfig]:
        prompt_path = Path(self.settings.chat_prompt_template_path)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).resolve().parents[4] / self.settings.chat_prompt_template_path
        text = prompt_path.read_text(encoding="utf-8").strip()
        return text, PromptConfig(
            template_id="interview-chat-system",
            version=self.settings.chat_prompt_version,
            max_history_entries=self.settings.chat_max_history_entries,
            include_retrieval_context=True,
        )

    def load_stage_prompt(self, stage: str) -> tuple[str, PromptConfig]:
        if stage not in {"quick", "detail"}:
            raise ValueError(f"unsupported_prompt_stage:{stage}")
        prompt_path = Path(self.settings.chat_prompt_template_path)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).resolve().parents[4] / self.settings.chat_prompt_template_path
        text = prompt_path.with_name(f"{stage}.md").read_text(encoding="utf-8").strip()
        return text, PromptConfig(
            template_id=f"interview-chat-{stage}",
            version=self.settings.chat_prompt_version,
            max_history_entries=self.settings.chat_max_history_entries,
            include_retrieval_context=stage == "detail",
        )


class InterviewPromptBuilder(PromptBuilderPort):
    def build(
        self,
        *,
        question: str,
        session_title: str,
        system_prompt: str,
        conversation_history: list[str],
        session_material_context_text: str,
        retrieval_context_text: str,
        prompt_config: PromptConfig,
    ) -> PromptBuildResult:
        selected_history = conversation_history[-prompt_config.max_history_entries :]
        answer_anchors = [item.removeprefix("本轮简要回答锚点：").strip() for item in selected_history if item.startswith("本轮简要回答锚点：")]
        history_text = "\n".join(item for item in selected_history if not item.startswith("本轮简要回答锚点："))
        sections = [
            "<authoritative_request>",
            f"会话标题：{session_title}\n当前问题：{question}",
            "</authoritative_request>",
        ]
        if history_text:
            sections.append(f"<untrusted_conversation_evidence>\n{history_text}\n</untrusted_conversation_evidence>")
        if session_material_context_text.strip():
            sections.append(f"<untrusted_fixed_material_evidence>\n{session_material_context_text.strip()}\n</untrusted_fixed_material_evidence>")
        if prompt_config.include_retrieval_context and retrieval_context_text.strip():
            sections.append(f"<untrusted_knowledge_evidence>\n{retrieval_context_text.strip()}\n</untrusted_knowledge_evidence>")
        elif prompt_config.include_retrieval_context:
            sections.append("<knowledge_status>本次未命中已确认知识库。</knowledge_status>")
        if answer_anchors:
            sections.append(f"<authoritative_answer_anchor>\n{answer_anchors[-1]}\n</authoritative_answer_anchor>")
        user_prompt = "\n\n".join(sections)
        return PromptBuildResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            rendered_prompt=f"{system_prompt}\n\n{user_prompt}",
            prompt_config=prompt_config,
            retrieval_excerpt_count=retrieval_context_text.count("["),
        )


class QwenCompatibleGateway(LLMGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        *,
        question: str,
        prompt: PromptBuildResult,
        stream: bool,
        attempt: int,
    ) -> GatewayAnswerResult:
        lowered = question.lower()
        if "__permanent_fail__" in lowered:
            raise NonRetryableChatError("forced_permanent_failure", code="forced_permanent_failure")
        if "__retry_once__" in lowered and attempt == 0:
            raise RetryableChatError("forced_retryable_failure", code="forced_retryable_failure")
        if self._should_use_remote_gateway():
            return self._generate_with_remote(question=question, prompt=prompt, stream=stream)
        answer = self._compose_answer(question=question, prompt=prompt)
        chunk_size = max(8, self.settings.chat_stream_chunk_chars)
        chunks = [
            ChatAnswerChunk(sequence=index + 1, text=answer[start:start + chunk_size], is_final=False)
            for index, start in enumerate(range(0, len(answer), chunk_size))
        ]
        if chunks:
            last = chunks[-1]
            chunks[-1] = ChatAnswerChunk(sequence=last.sequence, text=last.text, is_final=True)
        usage = UsageReport(
            prompt_tokens=max(1, len(prompt.rendered_prompt) // 4),
            completion_tokens=max(1, len(answer) // 4),
            total_tokens=max(1, len(prompt.rendered_prompt) // 4) + max(1, len(answer) // 4),
            provider_name="qwen-compatible",
            model_name=self.settings.chat_qwen_model,
        )
        return GatewayAnswerResult(
            provider_name="qwen-compatible",
            model_name=self.settings.chat_qwen_model,
            chunks=chunks if stream else [ChatAnswerChunk(sequence=1, text=answer, is_final=True)],
            final_text=answer,
            finish_reason="completed",
            usage=usage,
        )

    def stream_generate(
        self,
        *,
        question: str,
        prompt: PromptBuildResult,
        attempt: int,
    ) -> Iterator[ChatAnswerChunk]:
        lowered = question.lower()
        if "__permanent_fail__" in lowered:
            raise NonRetryableChatError("forced_permanent_failure", code="forced_permanent_failure")
        if "__retry_once__" in lowered and attempt == 0:
            raise RetryableChatError("forced_retryable_failure", code="forced_retryable_failure")
        if "__stream_fail_after_chunk__" in lowered:
            yield ChatAnswerChunk(sequence=1, text="这是已经生成的部分回答。", is_final=False)
            raise RetryableChatError("forced_stream_failure", code="forced_stream_failure")
        if self._should_use_remote_gateway():
            yield from self._stream_with_remote(prompt=prompt)
            return
        answer = self._compose_answer(question=question, prompt=prompt)
        chunks = self._chunk_answer(answer)
        for chunk in chunks:
            yield chunk

    def _should_use_remote_gateway(self) -> bool:
        if os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_CHAT") != "1":
            return False
        return True

    def _generate_with_remote(self, *, question: str, prompt: PromptBuildResult, stream: bool) -> GatewayAnswerResult:
        if not self.settings.chat_qwen_base_url or not self.settings.chat_qwen_api_key:
            raise NonRetryableChatError("当前对话模型未配置完成，请检查服务端 .env 配置。", code="chat_config_missing")
        body = self._request_completion(prompt=prompt)
        answer = self._extract_answer_text(body)
        if not answer:
            raise NonRetryableChatError("当前对话模型返回了无效结果，请稍后重试或检查模型配置。", code="chat_provider_invalid_response")
        usage_payload = body.get("usage", {}) if isinstance(body, dict) else {}
        usage = UsageReport(
            prompt_tokens=max(1, int(usage_payload.get("prompt_tokens", 0) or max(1, len(prompt.rendered_prompt) // 4))),
            completion_tokens=max(1, int(usage_payload.get("completion_tokens", 0) or max(1, len(answer) // 4))),
            total_tokens=max(1, int(usage_payload.get("total_tokens", 0) or (max(1, len(prompt.rendered_prompt) // 4) + max(1, len(answer) // 4)))),
            provider_name="qwen-compatible",
            model_name=self.settings.chat_qwen_model,
        )
        return GatewayAnswerResult(
            provider_name="qwen-compatible",
            model_name=self.settings.chat_qwen_model,
            chunks=self._chunk_answer(answer) if stream else [ChatAnswerChunk(sequence=1, text=answer, is_final=True)],
            final_text=answer,
            finish_reason="completed",
            usage=usage,
        )

    def _request_completion(self, *, prompt: PromptBuildResult) -> dict:
        response = self._post_completion(prompt=prompt, stream=False)
        try:
            body = response.json()
        except JSONDecodeError as exc:
            raise NonRetryableChatError("当前对话模型返回了无法解析的结果。", code="chat_provider_invalid_response") from exc
        if not isinstance(body, dict):
            raise NonRetryableChatError("当前对话模型返回了无效结果。", code="chat_provider_invalid_response")
        return body

    def _post_completion(self, *, prompt: PromptBuildResult, stream: bool) -> httpx.Response:
        base_url = self.settings.chat_qwen_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.settings.chat_qwen_model,
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": 1000,
            "enable_thinking": False,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
        }
        timeout_seconds = self.settings.integration_http_timeout_seconds
        started_at = _now_ms()
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {self.settings.chat_qwen_api_key}"}, json=payload)
        except httpx.HTTPError as exc:
            raise RetryableChatError("当前对话模型暂时不可用，请稍后重试。", code="chat_provider_unavailable") from exc
        finally:
            log_event(
                logging.getLogger(__name__),
                logging.INFO,
                settings=self.settings,
                event="chat.provider_request_finished",
                feature="live-answer",
                action="provider-request",
                duration_ms=_now_ms() - started_at,
                stream=stream,
                model=self.settings.chat_qwen_model,
            )
        self._raise_for_provider_status(response.status_code)
        return response

    def _raise_for_provider_status(self, status_code: int) -> None:
        if status_code in {401, 403}:
            raise NonRetryableChatError("当前对话模型鉴权失败，请检查服务配置。", code="chat_provider_auth_failed")
        if status_code == 429:
            raise RetryableChatError("当前对话模型请求过多，请稍后重试。", code="chat_provider_rate_limited")
        if status_code >= 500:
            raise RetryableChatError("当前对话模型暂时不可用，请稍后重试。", code="chat_provider_unavailable")
        if status_code >= 400:
            raise NonRetryableChatError("当前对话模型请求未通过，请检查会话或模型配置。", code="chat_provider_request_rejected")

    def _stream_with_remote(self, *, prompt: PromptBuildResult) -> Iterator[ChatAnswerChunk]:
        if not self.settings.chat_qwen_base_url or not self.settings.chat_qwen_api_key:
            raise NonRetryableChatError("当前对话模型未配置完成，请检查服务端 .env 配置。", code="chat_config_missing")
        base_url = self.settings.chat_qwen_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.settings.chat_qwen_model,
            "stream": True,
            "temperature": 0.2,
            "max_tokens": 520,
            "enable_thinking": False,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
        }
        sequence = 0
        timeout_seconds = self.settings.integration_http_timeout_seconds
        started_at = _now_ms()
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                with client.stream("POST", url, headers={"Authorization": f"Bearer {self.settings.chat_qwen_api_key}"}, json=payload) as response:
                    self._raise_for_provider_status(response.status_code)
                    for line in response.iter_lines():
                        text = self._extract_stream_line_text(line)
                        if not text:
                            continue
                        sequence += 1
                        yield ChatAnswerChunk(sequence=sequence, text=text, is_final=False)
        except httpx.HTTPError as exc:
            raise RetryableChatError("当前对话模型暂时不可用，请稍后重试。", code="chat_provider_unavailable") from exc
        finally:
            log_event(
                logging.getLogger(__name__),
                logging.INFO,
                settings=self.settings,
                event="chat.provider_stream_finished",
                feature="live-answer",
                action="provider-stream",
                duration_ms=_now_ms() - started_at,
                model=self.settings.chat_qwen_model,
                chunk_count=sequence,
            )

    def _extract_stream_line_text(self, line: str) -> str:
        if not line:
            return ""
        payload = line.strip()
        if not payload:
            return ""
        if payload.startswith("data:"):
            payload = payload[5:].strip()
        if payload == "[DONE]":
            return ""
        try:
            body = json.loads(payload)
        except JSONDecodeError:
            return ""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        delta = choices[0].get("delta") or choices[0].get("message") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(item.get("text", "") for item in content if isinstance(item, dict))
        return ""

    def _extract_answer_text(self, body: dict) -> str:
        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") in {None, "text"}]
                return "".join(part for part in text_parts if part).strip()
        return ""

    def _chunk_answer(self, answer: str) -> list[ChatAnswerChunk]:
        chunk_size = max(8, self.settings.chat_stream_chunk_chars)
        chunks = [
            ChatAnswerChunk(sequence=index + 1, text=answer[start:start + chunk_size], is_final=False)
            for index, start in enumerate(range(0, len(answer), chunk_size))
        ]
        if chunks:
            last = chunks[-1]
            chunks[-1] = ChatAnswerChunk(sequence=last.sequence, text=last.text, is_final=True)
        return chunks or [ChatAnswerChunk(sequence=1, text=answer, is_final=True)]

    def _compose_answer(self, *, question: str, prompt: PromptBuildResult) -> str:
        evidence_hint = "已结合本场资料和检索依据。" if prompt.retrieval_excerpt_count > 0 else "当前可用资料有限，建议结合你的真实经历补充。"
        return (
            "简要回答\n"
            f"围绕“{question}”，可以先直接给出核心结论，再点出与你真实经历最相关的一两个依据。"
            f"{evidence_hint}\n\n"
            "---\n\n"
            "详细回答\n"
            "我会先说明项目背景和目标，再展开你亲自负责的部分、关键决策和推进过程。"
            "接着补充为什么这样做，以及最后带来了什么结果或复盘收获。"
            "如果暂时没有可量化的数据，就诚实描述可观察到的改善，不要补造公司、项目、职责、结果或数字。"
        )


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        session_service: SessionService,
        retrieval_service: RetrievalPort,
        object_storage: FileStoragePort,
        repository: ChatRepository,
        prompt_template: PromptTemplatePort,
        prompt_builder: PromptBuilderPort,
        llm_gateway: LLMGatewayPort,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.session_service = session_service
        self.retrieval_service = retrieval_service
        self.object_storage = object_storage
        self.repository = repository
        self.prompt_template = prompt_template
        self.prompt_builder = prompt_builder
        self.llm_gateway = llm_gateway

    def _load_stage_prompt(self, stage: str) -> tuple[str, PromptConfig]:
        loader = getattr(self.prompt_template, "load_stage_prompt", None)
        return loader(stage) if callable(loader) else self.prompt_template.load_system_prompt()

    def _conversation_history(self, *, user_id: str, session_id: str, question: str) -> list[str]:
        entries = self.session_service.get_context_window(
            user_id=user_id,
            session_id=session_id,
            limit=self.settings.chat_max_history_entries + 1,
        )
        history = [f"{item.role}:{item.content}" for item in entries]
        if history and history[-1] == f"manual-question:{question.strip()}":
            history.pop()
        return history[-self.settings.chat_max_history_entries :]

    @staticmethod
    def _prompt_metadata(provenance: dict[str, object], *, stages: dict[str, str]) -> dict[str, object]:
        return {**provenance, "promptStrategyMode": "adaptive-evidence-first", "promptStages": stages}

    @staticmethod
    def _size_bucket(length: int) -> str:
        return "xs" if length <= 256 else "sm" if length <= 1000 else "md" if length <= 4000 else "lg"

    def answer_question(self, *, user_id: str, session_id: str, question: str, stream: bool) -> tuple[ChatAnswerTaskRecord, RetrievalResponse]:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("live-answer", "start", "只有进行中的面试会话才能发起实时回答。", 400)
        now_ms = _now_ms()
        task = self.repository.save_task(
            ChatAnswerTaskRecord(
                task_id=f"answer-{uuid4().hex}",
                session_id=session_id,
                owner_user_id=user_id,
                question=question.strip(),
                answer_text="",
                status="queued",
                stream_mode=stream,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        self._log(logging.INFO, "chat.started", task=task, session_id=session_id, question=question, retry_count=0)
        self.session_service.append_context(
            user_id=user_id,
            session_id=session_id,
            role="manual-question",
            source_kind="manual-input",
            content=question,
            visibility="session",
            related_task_id=task.task_id,
        )
        conversation_history = self._conversation_history(user_id=user_id, session_id=session_id, question=question)
        retrieval = self._retrieve_context(user_id=user_id, session=session, question=question)
        material_context_text, material_assembly, material_provenance = self._assemble_material_context(session=session, retrieval=retrieval)
        system_prompt, prompt_config = self.prompt_template.load_system_prompt()
        history_entries = self.session_service.get_context_window(user_id=user_id, session_id=session_id, limit=self.settings.chat_max_history_entries)
        prompt = self.prompt_builder.build(
            question=question,
            session_title=session.title,
            system_prompt=system_prompt,
            conversation_history=[f"{item.role}:{item.content}" for item in history_entries],
            session_material_context_text=material_context_text,
            retrieval_context_text=retrieval.context_text,
            prompt_config=prompt_config,
        )
        last_error: Exception | None = None
        current_task = replace(
            task,
            status="streaming",
            prompt_template_id=prompt.prompt_config.template_id,
            prompt_version=prompt.prompt_config.version,
            retrieval_excerpt_count=retrieval.final_count,
            material_context_status=material_assembly.status,
            fixed_source_count=material_assembly.fixed_source_count,
            retrieved_source_count=material_assembly.retrieved_source_count,
            material_provenance=material_provenance,
            unavailable_material_sources=[self._material_source_payload(item) for item in material_assembly.unavailable_sources],
            updated_at_ms=_now_ms(),
        )
        self.repository.save_task(current_task)
        for attempt in range(self.settings.chat_retry_max_attempts + 1):
            try:
                gateway_result = self.llm_gateway.generate(question=question, prompt=prompt, stream=stream, attempt=attempt)
                completed = self._complete_task(task=current_task, gateway_result=gateway_result, retry_count=attempt)
                self.session_service.append_context(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    source_kind="ai-answer",
                    content=completed.answer_text,
                    visibility="ai",
                    related_task_id=completed.task_id,
                )
                if gateway_result.usage is not None:
                    self.session_service.record_usage(
                        user_id=user_id,
                        session_id=session_id,
                        usage_kind="total",
                        prompt_tokens=gateway_result.usage.prompt_tokens,
                        completion_tokens=gateway_result.usage.completion_tokens,
                        total_tokens=gateway_result.usage.total_tokens,
                        provider_name=gateway_result.usage.provider_name,
                        model_name=gateway_result.usage.model_name,
                        related_task_id=completed.task_id,
                    )
                self._log(logging.INFO, "chat.completed", task=completed, session_id=session_id, question=question, retry_count=attempt)
                return completed, self._to_retrieval_response(retrieval)
            except RetryableChatError as exc:
                last_error = exc
                self._log(logging.WARNING, "chat.retrying", task=current_task, session_id=session_id, question=question, retry_count=attempt + 1, error_code=exc.code)
                continue
            except NonRetryableChatError as exc:
                last_error = exc
                break
        error_code = getattr(last_error, "code", last_error.__class__.__name__ if last_error else "chat_failed")
        failed = self.repository.save_task(
            replace(
                current_task,
                status="failed",
                retry_count=self.settings.chat_retry_max_attempts,
                error_code=error_code,
                error_message=str(last_error) if last_error else "chat_failed",
                updated_at_ms=_now_ms(),
                completed_at_ms=_now_ms(),
            )
        )
        self._log(logging.WARNING, "chat.failed", task=failed, session_id=session_id, question=question, retry_count=failed.retry_count, error_code=error_code)
        return failed, self._to_retrieval_response(retrieval)

    def stream_answer_question(self, *, user_id: str, session_id: str, question: str) -> Iterator[dict]:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("live-answer", "start-stream", "只有进行中的面试会话才能发起实时回答。", 400)
        now_ms = _now_ms()
        task = self.repository.save_task(
            ChatAnswerTaskRecord(
                task_id=f"answer-{uuid4().hex}",
                session_id=session_id,
                owner_user_id=user_id,
                question=question.strip(),
                answer_text="",
                status="queued",
                stream_mode=True,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        self._log(logging.INFO, "chat.stream_started", task=task, session_id=session_id, question=question, retry_count=0)
        self.session_service.append_context(
            user_id=user_id,
            session_id=session_id,
            role="manual-question",
            source_kind="manual-input",
            content=question,
            visibility="session",
            related_task_id=task.task_id,
        )
        quick_retrieval = RetrievalContext(
            normalized_question=question.strip(),
            context_text="",
            chunks=[],
            candidate_count=0,
            final_count=0,
            strategy="filtered-first",
        )
        material_context_text, material_assembly, material_provenance = self._assemble_material_context(session=session, retrieval=quick_retrieval)
        quick_system_prompt, prompt_config = self._load_stage_prompt("quick")
        material_context_text = material_context_text[:min(2400, int(getattr(self.settings, "rag_context_max_characters", 6000)))]
        conversation_history = self._conversation_history(
            user_id=user_id,
            session_id=session_id,
            question=question,
        )
        prompt = self.prompt_builder.build(
            question=question,
            session_title=session.title,
            system_prompt=quick_system_prompt,
            conversation_history=conversation_history,
            session_material_context_text=material_context_text,
            retrieval_context_text="",
            prompt_config=prompt_config,
        )
        current_task = self.repository.save_task(
            replace(
                task,
                status="streaming",
                provider_name="qwen-compatible",
                model_name=self.settings.chat_qwen_model,
                prompt_template_id=prompt.prompt_config.template_id,
                prompt_version=prompt.prompt_config.version,
                retrieval_excerpt_count=quick_retrieval.final_count,
                material_context_status=material_assembly.status,
                fixed_source_count=material_assembly.fixed_source_count,
                retrieved_source_count=material_assembly.retrieved_source_count,
                material_provenance=self._prompt_metadata(
                    material_provenance,
                    stages={"quick": f"{prompt.prompt_config.template_id}:{prompt.prompt_config.version}"},
                ),
                unavailable_material_sources=[self._material_source_payload(item) for item in material_assembly.unavailable_sources],
                updated_at_ms=_now_ms(),
            )
        )
        yield {"type": "task-started", "task": current_task, "retrieval": self._to_retrieval_response(quick_retrieval)}
        chunks: list[ChatAnswerChunk] = []
        answer_parts: list[str] = []
        last_error: Exception | None = None
        stream_started_at_ms = _now_ms()
        first_token_at_ms: int | None = None
        for attempt in range(self.settings.chat_retry_max_attempts + 1):
            try:
                if self._is_task_cancelled(current_task.task_id):
                    cancelled = self.repository.get_task(current_task.task_id) or current_task
                    yield {"type": "cancelled", "task": cancelled}
                    return
                for seed_text in ["简单回答\n"]:
                    normalized = ChatAnswerChunk(sequence=len(chunks) + 1, text=seed_text, is_final=False)
                    chunks.append(normalized)
                    answer_parts.append(normalized.text)
                    current_task = self.repository.save_task(
                        replace(current_task, chunks=chunks.copy(), answer_text="".join(answer_parts), retry_count=attempt, updated_at_ms=_now_ms())
                    )
                    yield {"type": "chunk", "task": current_task, "chunk": normalized}
                for chunk in self.llm_gateway.stream_generate(question=question, prompt=prompt, attempt=attempt):
                    if self._is_task_cancelled(current_task.task_id):
                        cancelled = self.repository.get_task(current_task.task_id) or current_task
                        yield {"type": "cancelled", "task": cancelled}
                        return
                    if first_token_at_ms is None:
                        first_token_at_ms = _now_ms()
                    normalized = ChatAnswerChunk(sequence=len(chunks) + 1, text=chunk.text, is_final=False)
                    chunks.append(normalized)
                    answer_parts.append(normalized.text)
                    current_task = self.repository.save_task(
                        replace(current_task, chunks=chunks.copy(), answer_text="".join(answer_parts), retry_count=attempt, updated_at_ms=_now_ms())
                    )
                    yield {"type": "chunk", "task": current_task, "chunk": normalized}
                retrieval = self._retrieve_context(user_id=user_id, session=session, question=question)
                if self._is_task_cancelled(current_task.task_id):
                    cancelled = self.repository.get_task(current_task.task_id) or current_task
                    yield {"type": "cancelled", "task": cancelled}
                    return
                material_context_text, material_assembly, material_provenance = self._assemble_material_context(session=session, retrieval=retrieval)
                detail_system_prompt, detail_prompt_config = self._load_stage_prompt("detail")
                quick_answer_anchor = "".join(answer_parts).removeprefix("简单回答\n").strip()
                detail_prompt = self.prompt_builder.build(
                    question=question,
                    session_title=session.title,
                    system_prompt=detail_system_prompt,
                    conversation_history=[*conversation_history, f"本轮简要回答锚点：{quick_answer_anchor}"],
                    session_material_context_text=material_context_text[:int(getattr(self.settings, "rag_context_max_characters", 6000))],
                    retrieval_context_text=retrieval.context_text,
                    prompt_config=detail_prompt_config,
                )
                current_task = self.repository.save_task(
                    replace(
                        current_task,
                        prompt_template_id="interview-chat-quick+detail",
                        prompt_version=detail_prompt.prompt_config.version,
                        retrieval_excerpt_count=retrieval.final_count,
                        material_context_status=material_assembly.status,
                        fixed_source_count=material_assembly.fixed_source_count,
                        retrieved_source_count=material_assembly.retrieved_source_count,
                        material_provenance=self._prompt_metadata(
                            material_provenance,
                            stages={
                                "quick": f"{prompt.prompt_config.template_id}:{prompt.prompt_config.version}",
                                "detail": f"{detail_prompt.prompt_config.template_id}:{detail_prompt.prompt_config.version}",
                            },
                        ),
                        unavailable_material_sources=[self._material_source_payload(item) for item in material_assembly.unavailable_sources],
                        updated_at_ms=_now_ms(),
                    )
                )
                separator = "\n\n---\n\n详细回答\n"
                normalized = ChatAnswerChunk(sequence=len(chunks) + 1, text=separator, is_final=False)
                chunks.append(normalized)
                answer_parts.append(normalized.text)
                current_task = self.repository.save_task(
                    replace(current_task, chunks=chunks.copy(), answer_text="".join(answer_parts), retry_count=attempt, updated_at_ms=_now_ms())
                )
                yield {"type": "chunk", "task": current_task, "chunk": normalized}
                for chunk in self.llm_gateway.stream_generate(question=question, prompt=detail_prompt, attempt=attempt):
                    if self._is_task_cancelled(current_task.task_id):
                        cancelled = self.repository.get_task(current_task.task_id) or current_task
                        yield {"type": "cancelled", "task": cancelled}
                        return
                    normalized = ChatAnswerChunk(sequence=len(chunks) + 1, text=chunk.text, is_final=False)
                    chunks.append(normalized)
                    answer_parts.append(normalized.text)
                    current_task = self.repository.save_task(
                        replace(current_task, chunks=chunks.copy(), answer_text="".join(answer_parts), retry_count=attempt, updated_at_ms=_now_ms())
                    )
                    yield {"type": "chunk", "task": current_task, "chunk": normalized}
                final_text = "".join(answer_parts).strip()
                if not final_text:
                    raise NonRetryableChatError("当前对话模型返回了无效结果，请稍后重试或检查模型配置。", code="chat_provider_invalid_response")
                if chunks:
                    last = chunks[-1]
                    chunks[-1] = ChatAnswerChunk(sequence=last.sequence, text=last.text, is_final=True)
                usage = UsageReport(
                    prompt_tokens=max(1, (len(prompt.rendered_prompt) + len(detail_prompt.rendered_prompt)) // 4),
                    completion_tokens=max(1, len(final_text) // 4),
                    total_tokens=max(1, (len(prompt.rendered_prompt) + len(detail_prompt.rendered_prompt)) // 4) + max(1, len(final_text) // 4),
                    provider_name="qwen-compatible",
                    model_name=self.settings.chat_qwen_model,
                )
                completed = self._complete_task(
                    task=current_task,
                    gateway_result=GatewayAnswerResult(
                        provider_name="qwen-compatible",
                        model_name=self.settings.chat_qwen_model,
                        chunks=chunks.copy(),
                        final_text=final_text,
                        finish_reason="completed",
                        usage=usage,
                    ),
                    retry_count=attempt,
                )
                self.session_service.append_context(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    source_kind="ai-answer",
                    content=completed.answer_text,
                    visibility="ai",
                    related_task_id=completed.task_id,
                )
                self.session_service.record_usage(
                    user_id=user_id,
                    session_id=session_id,
                    usage_kind="total",
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    provider_name=usage.provider_name,
                    model_name=usage.model_name,
                    related_task_id=completed.task_id,
                )
                log_event(
                    self.logger, logging.INFO, settings=self.settings,
                    event="chat.prompt_quality_completed", feature="live-answer", action="prompt-quality",
                    session_id=session_id, task_id=completed.task_id,
                    prompt_template_id=completed.prompt_template_id, prompt_version=completed.prompt_version,
                    prompt_strategy_mode="adaptive-evidence-first",
                    fixed_source_count=completed.fixed_source_count, retrieved_source_count=completed.retrieved_source_count,
                    question_size_bucket=self._size_bucket(len(question)), answer_size_bucket=self._size_bucket(len(completed.answer_text)),
                    first_token_ms=(first_token_at_ms - stream_started_at_ms) if first_token_at_ms is not None else None,
                    completion_ms=_now_ms() - stream_started_at_ms, status=completed.status,
                )
                self._log(logging.INFO, "chat.stream_completed", task=completed, session_id=session_id, question=question, retry_count=attempt)
                yield {"type": "completed", "task": completed, "retrieval": self._to_retrieval_response(retrieval)}
                return
            except RetryableChatError as exc:
                last_error = exc
                self._log(logging.WARNING, "chat.stream_retrying", task=current_task, session_id=session_id, question=question, retry_count=attempt + 1, error_code=exc.code)
                if chunks:
                    break
                continue
            except NonRetryableChatError as exc:
                last_error = exc
                break
        error_code = getattr(last_error, "code", last_error.__class__.__name__ if last_error else "chat_failed")
        failed = self.repository.save_task(
            replace(
                current_task,
                status="failed",
                chunks=chunks.copy(),
                answer_text="".join(answer_parts),
                retry_count=self.settings.chat_retry_max_attempts,
                error_code=error_code,
                error_message=str(last_error) if last_error else "chat_failed",
                updated_at_ms=_now_ms(),
                completed_at_ms=_now_ms(),
            )
        )
        self._log(logging.WARNING, "chat.stream_failed", task=failed, session_id=session_id, question=question, retry_count=failed.retry_count, error_code=error_code)
        yield {"type": "failed", "task": failed, "error_code": error_code, "error_message": failed.error_message, "partial_text": failed.answer_text}

    def get_task(self, *, user_id: str, task_id: str) -> ChatAnswerTaskRecord:
        task = self.repository.get_task(task_id)
        if task is None:
            raise DomainRequestError("live-answer", "get-task", "回答任务不存在。", 404)
        if task.owner_user_id != user_id:
            raise DomainRequestError("live-answer", "get-task", "不能查看其他用户的回答任务。", 403)
        return task

    def cancel_task(self, *, user_id: str, task_id: str, expected_revision: int | None = None) -> tuple[str, ChatAnswerTaskRecord]:
        task = self.get_task(user_id=user_id, task_id=task_id)
        revision = max(1, task.updated_at_ms)
        if expected_revision is not None and expected_revision not in {0, 1, revision}:
            return "stale-revision", task
        if task.status == "cancelled":
            return "already-cancelled", task
        if task.status not in {"queued", "streaming"}:
            return "not-cancellable", task
        cancelled = self.repository.save_task(replace(task, status="cancelled", updated_at_ms=_now_ms(), completed_at_ms=_now_ms()))
        return "cancelled", cancelled

    def _is_task_cancelled(self, task_id: str) -> bool:
        task = self.repository.get_task(task_id)
        return task is not None and task.status == "cancelled"

    def list_session_history(self, *, user_id: str, session_id: str) -> list[ChatAnswerTaskRecord]:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return self.repository.list_tasks_for_session(session_id=session_id)

    def _complete_task(self, *, task: ChatAnswerTaskRecord, gateway_result: GatewayAnswerResult, retry_count: int) -> ChatAnswerTaskRecord:
        completed = replace(
            task,
            answer_text=gateway_result.final_text,
            status="completed",
            provider_name=gateway_result.provider_name,
            model_name=gateway_result.model_name,
            chunks=gateway_result.chunks,
            retry_count=retry_count,
            updated_at_ms=_now_ms(),
            completed_at_ms=_now_ms(),
        )
        return self.repository.save_task(completed)

    def _retrieve_context(self, *, user_id: str, session, question: str):
        try:
            knowledge_documents = [document for document in session.material_binding.bound_documents if document.active and document.document_kind == "knowledge"]
            context = self.retrieval_service.retrieve(
                question=question,
                filter=RetrievalFilter(
                    owner_user_id=user_id,
                    interview_session_id=session.session_id,
                    document_kinds=["knowledge"] if knowledge_documents else [],
                    document_ids=[document.document_id for document in knowledge_documents],
                    document_version_ids=[
                        document.document_version_id
                        for document in knowledge_documents
                        if document.document_version_id
                    ],
                    knowledge_collection_ids=[
                        document.knowledge_collection_id
                        for document in knowledge_documents
                        if document.knowledge_collection_id
                    ],
                ),
                candidate_top_k=min(self.settings.retrieval_candidate_top_k, 6),
                final_top_k=min(self.settings.retrieval_final_top_k, 3),
                strategy=self.settings.retrieval_strategy,  # type: ignore[arg-type]
            )
            return context
        except Exception as exc:
            self._log(
                logging.WARNING,
                "chat.retrieval_degraded",
                task=None,
                session_id=session.session_id,
                question=question,
                retry_count=0,
                error_code=exc.__class__.__name__,
            )
            from app.ports.retrieval import RetrievalContext

            return RetrievalContext(
                normalized_question=question.strip(),
                context_text="",
                chunks=[],
                candidate_count=0,
                final_count=0,
                strategy="filtered-first",
            )

    def _assemble_material_context(self, *, session, retrieval) -> tuple[str, MaterialContextAssembly, dict[str, object]]:
        lines: list[str] = []
        used_sources: list[MaterialContextSource] = []
        unavailable_sources: list[MaterialContextSource] = []
        for label, kind in (("简历", "resume"), ("职位 JD", "job_description")):
            document = next((item for item in session.material_binding.bound_documents if item.active and item.document_kind == kind), None)
            if document is None:
                continue
            content, truncated = self._load_material_summary_for_prompt(document)
            source = MaterialContextSource(
                source_id=document.document_id,
                source_version=document.document_version_id or document.document_id,
                display_name=document.display_name,
                kind="jd" if document.document_kind == "job_description" else document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                context_role="fixed",
                evidence_summary=(content[:80].replace("\n", " ") if content else None),
                truncated=truncated,
                unavailable=not bool(content),
                unavailable_reason=None if content else "material_summary_unavailable",
            )
            if content:
                used_sources.append(source)
                lines.append(f"[{label}] {document.display_name} ({document.document_version_id or document.document_id})\n{content}")
            else:
                unavailable_sources.append(source)
                lines.append(f"[{label}] {document.display_name}：资料已选择，但面试摘要当前不可用，本次回答不得声称已使用该资料细节。")
        retrieved_by_document: dict[str, list] = {}
        for chunk in retrieval.chunks:
            retrieved_by_document.setdefault(chunk.document_id, []).append(chunk)
        for document in [item for item in session.material_binding.bound_documents if item.active and item.document_kind == "knowledge"]:
            chunks = retrieved_by_document.get(document.document_id, [])
            if not chunks:
                continue
            first = chunks[0]
            used_sources.append(
                MaterialContextSource(
                    source_id=document.document_id,
                    source_version=document.document_version_id or document.document_id,
                    display_name=document.display_name,
                    kind="knowledge",
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    context_role="retrieved",
                    evidence_summary=first.content[:80].replace("\n", " "),
                    retrieval_count=len(chunks),
                    truncated=False,
                )
            )
        status = "ready" if used_sources and not unavailable_sources else "degraded" if used_sources or unavailable_sources else "no-context"
        assembly = MaterialContextAssembly(
            status=status,
            fixed_source_count=len([item for item in used_sources if item.context_role == "fixed"]),
            retrieved_source_count=len([item for item in used_sources if item.context_role == "retrieved"]),
            used_sources=used_sources,
            unavailable_sources=unavailable_sources,
        )
        provenance = {
            "selectionRevision": session.material_binding.revision,
            "usedSources": [self._material_source_payload(item) for item in used_sources],
            "unavailableSources": [self._material_source_payload(item) for item in unavailable_sources],
            "fixedSourceCount": assembly.fixed_source_count,
            "retrievedSourceCount": assembly.retrieved_source_count,
            "noPersonalMaterialUsed": not used_sources,
            "retrievalTraceId": getattr(retrieval, "trace_id", None),
        }
        return "\n\n".join(lines), assembly, provenance

    def _session_material_prompt_context(self, session) -> str:
        return self._assemble_material_context(session=session, retrieval=type("EmptyRetrieval", (), {"chunks": []})())[0]

    def _load_material_summary_for_prompt(self, document) -> tuple[str, bool]:
        summary = (document.summary or "").strip()
        if not summary:
            return "", False
        generic_prefixes = (
            "文档处理完成",
            "文档处理中",
            "文档已重新进入处理队列",
            "文档解析失败",
            "文档向量化失败",
            "文档处理失败",
        )
        if any(summary.startswith(prefix) for prefix in generic_prefixes):
            return "", False
        limit = 900 if document.document_kind == "resume" else 700
        truncated = len(summary) > limit
        return summary[:limit] + ("\n\n[资料摘要已截断]" if truncated else ""), truncated

    def _material_source_payload(self, source: MaterialContextSource) -> dict[str, object]:
        return {
            "sourceId": source.source_id,
            "sourceVersion": source.source_version,
            "displayName": source.display_name,
            "kind": source.kind,
            "documentId": source.document_id,
            "documentVersionId": source.document_version_id,
            "contextRole": source.context_role,
            "evidenceSummary": source.evidence_summary,
            "retrievalCount": source.retrieval_count,
            "truncated": source.truncated,
            "unavailable": source.unavailable,
            "unavailableReason": source.unavailable_reason,
        }

    def _to_retrieval_response(self, retrieval) -> RetrievalResponse:
        return RetrievalResponse(
            normalizedQuestion=retrieval.normalized_question,
            contextText=retrieval.context_text,
            chunks=[
                RetrievedChunkResponse(
                    documentId=chunk.document_id,
                    documentKind=chunk.document_kind,
                    chunkId=chunk.chunk_id,
                    chunkIndex=chunk.chunk_index,
                    content=chunk.content,
                    score=chunk.score,
                    rerankScore=chunk.rerank_score,
                    metadata=chunk.metadata,
                )
                for chunk in retrieval.chunks
            ],
            candidateCount=retrieval.candidate_count,
            finalCount=retrieval.final_count,
            strategy=retrieval.strategy,
        )

    def _log(self, level: int, event: str, *, task: ChatAnswerTaskRecord | None, session_id: str, question: str, retry_count: int, error_code: str | None = None) -> None:
        log_event(
            self.logger,
            level,
            settings=self.settings,
            event=event,
            feature="live-answer",
            action="chat",
            session_id=session_id,
            task_id=task.task_id if task else None,
            provider_name=task.provider_name if task else None,
            model_name=task.model_name if task else None,
            prompt_version=task.prompt_version if task else None,
            stream_mode=task.stream_mode if task else None,
            status=task.status if task else None,
            retry_count=retry_count,
            retrieval_excerpt_count=task.retrieval_excerpt_count if task else None,
            question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest()[:12],
            question_length=len(question),
            error_code=error_code,
        )
