from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator
from typing import Literal, Protocol


AnswerTaskStatus = Literal["queued", "streaming", "completed", "failed", "cancelled"]
ChatFinishReason = Literal["completed", "failed", "cancelled", "retry-exhausted"]


@dataclass(frozen=True)
class PromptConfig:
    template_id: str
    version: str
    max_history_entries: int
    include_retrieval_context: bool = True


@dataclass(frozen=True)
class PromptBuildResult:
    system_prompt: str
    user_prompt: str
    rendered_prompt: str
    prompt_config: PromptConfig
    retrieval_excerpt_count: int


@dataclass(frozen=True)
class ChatAnswerChunk:
    sequence: int
    text: str
    is_final: bool = False


@dataclass(frozen=True)
class MaterialContextSource:
    source_id: str
    source_version: str
    display_name: str
    kind: str
    document_id: str | None = None
    document_version_id: str | None = None
    context_role: str = "fixed"
    evidence_summary: str | None = None
    retrieval_count: int = 0
    truncated: bool = False
    unavailable: bool = False
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class MaterialContextAssembly:
    status: str
    fixed_source_count: int = 0
    retrieved_source_count: int = 0
    used_sources: list[MaterialContextSource] = field(default_factory=list)
    unavailable_sources: list[MaterialContextSource] = field(default_factory=list)


@dataclass(frozen=True)
class UsageReport:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class GatewayAnswerResult:
    provider_name: str
    model_name: str
    chunks: list[ChatAnswerChunk] = field(default_factory=list)
    final_text: str = ""
    finish_reason: ChatFinishReason = "completed"
    usage: UsageReport | None = None


@dataclass(frozen=True)
class ChatAnswerTaskRecord:
    task_id: str
    session_id: str
    owner_user_id: str
    question: str
    answer_text: str
    status: AnswerTaskStatus
    stream_mode: bool
    provider_name: str | None = None
    model_name: str | None = None
    prompt_template_id: str | None = None
    prompt_version: str | None = None
    retrieval_excerpt_count: int = 0
    material_context_status: str = "not-assembled"
    fixed_source_count: int = 0
    retrieved_source_count: int = 0
    material_provenance: dict[str, object] = field(default_factory=dict)
    unavailable_material_sources: list[dict[str, object]] = field(default_factory=list)
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    completed_at_ms: int | None = None
    chunks: list[ChatAnswerChunk] = field(default_factory=list)


class PromptBuilderPort(Protocol):
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
    ) -> PromptBuildResult: ...


class PromptTemplatePort(Protocol):
    def load_system_prompt(self) -> tuple[str, PromptConfig]: ...

    def load_stage_prompt(self, stage: str) -> tuple[str, PromptConfig]: ...


class LLMGatewayPort(Protocol):
    def generate(
        self,
        *,
        question: str,
        prompt: PromptBuildResult,
        stream: bool,
        attempt: int,
    ) -> GatewayAnswerResult: ...

    def stream_generate(
        self,
        *,
        question: str,
        prompt: PromptBuildResult,
        attempt: int,
    ) -> Iterator[ChatAnswerChunk]: ...


class ChatRepository(Protocol):
    def save_task(self, task: ChatAnswerTaskRecord) -> ChatAnswerTaskRecord: ...

    def get_task(self, task_id: str) -> ChatAnswerTaskRecord | None: ...

    def list_tasks_for_session(self, *, session_id: str) -> list[ChatAnswerTaskRecord]: ...
