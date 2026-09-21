from __future__ import annotations

import json
import logging

import pytest

from app.core.config import get_settings
from app.ports.chat import ChatAnswerChunk, PromptBuildResult, PromptConfig
from app.services.chat_service import ChatService, FilePromptTemplateAdapter, InterviewPromptBuilder, NonRetryableChatError, QwenCompatibleGateway


def _prompt(template_id: str) -> PromptBuildResult:
    return PromptBuildResult(
        system_prompt="system",
        user_prompt="user",
        rendered_prompt="system\n\nuser",
        prompt_config=PromptConfig(template_id=template_id, version="test", max_history_entries=1),
        retrieval_excerpt_count=0,
    )


def test_gateway_extracts_safe_finish_reasons_and_keeps_missing_reason_compatible() -> None:
    gateway = QwenCompatibleGateway(get_settings())

    assert gateway._extract_stream_line('data: {"choices":[{"delta":{"content":"完整"},"finish_reason":"stop"}]}') == ("完整", "stop")
    assert gateway._extract_stream_line('data: {"choices":[{"delta":{},"finish_reason":"length"}]}') == ("", "length")
    assert gateway._extract_stream_line('data: {"choices":[{"delta":{"content":"片段"},"finish_reason":null}]}') == ("片段", None)
    assert gateway._extract_stream_line('data: {"choices":[{"delta":{},"finish_reason":"unexpected"}]}') == ("", "unknown")


def test_gateway_uses_stage_specific_token_budgets() -> None:
    settings = get_settings().model_copy(update={
        "chat_quick_max_tokens": 321,
        "chat_detail_max_tokens": 987,
        "chat_continuation_max_tokens": 654,
    })
    gateway = QwenCompatibleGateway(settings)

    assert gateway._max_tokens_for_prompt(_prompt("interview-chat-quick")) == 321
    assert gateway._max_tokens_for_prompt(_prompt("interview-chat-detail")) == 987
    assert gateway._max_tokens_for_prompt(_prompt("interview-chat-continuation-detail")) == 654


def test_gateway_routes_quick_and_detail_stages_to_their_dedicated_models() -> None:
    settings = get_settings().model_copy(update={
        "chat_qwen_model": "shared-model",
        "chat_quick_model": "quick-model",
        "chat_detail_model": "detail-model",
    })
    gateway = QwenCompatibleGateway(settings)

    assert gateway._model_for_prompt(_prompt("interview-chat-quick")) == "quick-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-en-quick")) == "quick-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-continuation-quick")) == "quick-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-detail")) == "detail-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-continuation-detail")) == "detail-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-generic")) == "shared-model"


def test_prompt_builder_repeats_machine_readable_protocol_only_for_quick_stage() -> None:
    builder = InterviewPromptBuilder()
    quick = builder.build(
        question="如何保证服务稳定？",
        session_title="合成面试",
        system_prompt="policy",
        conversation_history=[],
        session_material_context_text="",
        retrieval_context_text="",
        prompt_config=_prompt("interview-chat-quick").prompt_config,
    )
    detail = builder.build(
        question="如何保证服务稳定？",
        session_title="合成面试",
        system_prompt="policy",
        conversation_history=[],
        session_material_context_text="",
        retrieval_context_text="",
        prompt_config=_prompt("interview-chat-detail").prompt_config,
    )

    assert quick.user_prompt.endswith("</required_output_protocol>")
    assert "你的第一个字符必须是<normalized_question>" in quick.user_prompt
    assert "<required_output_protocol>" not in detail.user_prompt


@pytest.mark.parametrize("quick_model", [None, "", "   "])
def test_gateway_quick_model_falls_back_to_shared_model(quick_model: str | None) -> None:
    settings = get_settings().model_copy(update={
        "chat_qwen_model": "shared-model",
        "chat_quick_model": quick_model,
    })
    gateway = QwenCompatibleGateway(settings)

    assert gateway._model_for_prompt(_prompt("interview-chat-quick")) == "shared-model"


@pytest.mark.parametrize("detail_model", [None, "", "   "])
def test_gateway_detail_model_falls_back_to_shared_model(detail_model: str | None) -> None:
    settings = get_settings().model_copy(update={
        "chat_qwen_model": "shared-model",
        "chat_detail_model": detail_model,
    })
    gateway = QwenCompatibleGateway(settings)

    assert gateway._model_for_prompt(_prompt("interview-chat-detail")) == "shared-model"
    assert gateway._model_for_prompt(_prompt("interview-chat-continuation-detail")) == "shared-model"


def test_gateway_sends_and_logs_actual_stage_models_without_prompt_content(caplog: pytest.LogCaptureFixture) -> None:
    class FakeResponse:
        status_code = 200

    class FakeHttpClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def post(self, _url, *, headers, json):
            self.payloads.append(json)
            return FakeResponse()

        def close(self) -> None:
            return None

    settings = get_settings().model_copy(update={
        "chat_qwen_base_url": "https://provider.example/v1",
        "chat_qwen_api_key": "synthetic-test-key",
        "chat_qwen_model": "shared-model",
        "chat_quick_model": "deepseek-v4.1-flash",
        "chat_detail_model": "deepseek-v4.1-flash",
    })
    client = FakeHttpClient()
    gateway = QwenCompatibleGateway(settings, http_client=client)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        gateway._post_completion(prompt=_prompt("interview-chat-quick"), stream=False)
        gateway._post_completion(prompt=_prompt("interview-chat-detail"), stream=False)

    assert [payload["model"] for payload in client.payloads] == ["deepseek-v4.1-flash", "deepseek-v4.1-flash"]
    events = [json.loads(record.message) for record in caplog.records if '"event": "chat.provider_request_finished"' in record.message]
    assert [(event["stage"], event["model"]) for event in events[-2:]] == [
        ("quick", "deepseek-v4.1-flash"),
        ("detail", "deepseek-v4.1-flash"),
    ]
    assert all("system" not in record.message and "user" not in record.message for record in caplog.records)


@pytest.mark.parametrize(
    ("template_id", "expected_model"),
    [
        ("interview-chat-quick", "quick-model"),
        ("interview-chat-detail", "detail-model"),
    ],
)
def test_remote_gateway_result_reports_actual_stage_model(
    monkeypatch: pytest.MonkeyPatch,
    template_id: str,
    expected_model: str,
) -> None:
    settings = get_settings().model_copy(update={
        "chat_qwen_base_url": "https://provider.example/v1",
        "chat_qwen_api_key": "synthetic-test-key",
        "chat_qwen_model": "shared-model",
        "chat_quick_model": "quick-model",
        "chat_detail_model": "detail-model",
    })
    gateway = QwenCompatibleGateway(settings)
    monkeypatch.setattr(gateway, "_request_completion", lambda *, prompt: {
        "choices": [{"message": {"content": "合成回答。"}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
    })

    result = gateway._generate_with_remote(
        question="合成问题",
        prompt=_prompt(template_id),
        stream=False,
    )

    assert result.model_name == expected_model
    assert result.usage is not None
    assert result.usage.model_name == expected_model


def test_gateway_reuses_and_closes_one_injected_http_client() -> None:
    class FakeHttpClient:
        def __init__(self) -> None:
            self.closed = 0

        def close(self) -> None:
            self.closed += 1

    client = FakeHttpClient()
    gateway = QwenCompatibleGateway(get_settings(), http_client=client)  # type: ignore[arg-type]

    assert gateway._client() is client
    assert gateway._client() is client

    gateway.close()
    assert client.closed == 1


def test_incomplete_detection_covers_length_dangling_syntax_and_code_fences() -> None:
    assert ChatService._answer_looks_incomplete("回答完整。", "stop") is False
    assert ChatService._answer_looks_incomplete("回答到了长度上限。", "length") is True
    assert ChatService._answer_looks_incomplete("下一步需要检查：", "stop") is True
    assert ChatService._answer_looks_incomplete("```python\nprint('ok')", "stop") is True


def test_overlap_merge_never_duplicates_repeated_provider_prefix() -> None:
    merged, appended = ChatService._append_without_overlap("先扩容消费者", "扩容消费者，再限制重试次数。")

    assert merged == "先扩容消费者，再限制重试次数。"
    assert appended == "，再限制重试次数。"


class _ScriptedGateway:
    def __init__(self, scripts: list[list[ChatAnswerChunk]]) -> None:
        self.scripts = scripts
        self.calls: list[str] = []

    def stream_generate(self, *, question, prompt, attempt):
        self.calls.append(prompt.prompt_config.template_id)
        yield from self.scripts.pop(0)


def _service_with_gateway(gateway: _ScriptedGateway, *, max_attempts: int = 2) -> ChatService:
    service = ChatService.__new__(ChatService)
    service.settings = get_settings().model_copy(update={"chat_continuation_max_attempts": max_attempts})
    service.logger = logging.getLogger("test-chat-answer-completeness")
    service.llm_gateway = gateway
    service.prompt_template = FilePromptTemplateAdapter(service.settings)
    service._is_task_cancelled = lambda _task_id: False
    return service


@pytest.mark.parametrize("stage", ["quick", "detail"])
def test_each_answer_stage_continues_length_truncation_without_duplication(stage: str) -> None:
    gateway = _ScriptedGateway([[
        ChatAnswerChunk(sequence=1, text="扩容消费者，并限制重试次数。", is_final=True, provider_finish_reason="stop")
    ]])
    service = _service_with_gateway(gateway)

    suffix, continuation_count, prompt_characters = service._complete_answer_stage(
        stage=stage,
        question="如何处理消息积压？",
        prompt=_prompt(f"interview-chat-{stage}"),
        existing_answer="先确认积压速度，再扩容消费者",
        finish_reason="length",
        provider_attempt=0,
        task_id="task-complete",
    )

    assert suffix == "，并限制重试次数。"
    assert continuation_count == 1
    assert prompt_characters > 0
    assert gateway.calls == [f"interview-chat-continuation-{stage}"]


def test_continuation_exhaustion_never_reports_completion() -> None:
    gateway = _ScriptedGateway([
        [ChatAnswerChunk(sequence=1, text="仍然没有结束，", is_final=True, provider_finish_reason="length")],
        [ChatAnswerChunk(sequence=1, text="继续但还是，", is_final=True, provider_finish_reason="length")],
    ])
    service = _service_with_gateway(gateway, max_attempts=2)

    with pytest.raises(NonRetryableChatError) as error:
        service._complete_answer_stage(
            stage="detail",
            question="请完整回答",
            prompt=_prompt("interview-chat-detail"),
            existing_answer="回答开始，",
            finish_reason="length",
            provider_attempt=0,
            task_id="task-incomplete",
        )

    assert error.value.code == "chat_answer_incomplete"
    assert error.value.partial_suffix == "仍然没有结束，继续但还是，"
