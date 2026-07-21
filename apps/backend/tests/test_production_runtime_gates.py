from __future__ import annotations

import pytest

from app import deps
from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services.document_processing_adapters import SyntheticEmbeddingAdapter
from app.services.knowledge_retrieval import HeuristicRerankerAdapter, SyntheticQueryEmbeddingAdapter
from app.services.realtime_speech_service import SyntheticRealtimeAsrGateway
from app.services.screenshot_answer_service import SyntheticVisionGateway
from app.services.sms_verification_provider import FakeSmsVerificationProvider


FACTORIES = (
    deps.llm_gateway_port,
    deps.sms_verification_provider,
    deps.screenshot_vision_gateway,
    deps.realtime_asr_gateway,
    deps.document_parser_adapter,
    deps.embedding_adapter,
    deps.query_embedding_adapter,
    deps.reranker_adapter,
)


def isolated_settings(environment: str) -> Settings:
    return Settings(
        _env_file=None,
        environment=environment,
        chat_qwen_base_url=None,
        chat_qwen_api_key=None,
        auth_sms_provider_mode="fake",
        auth_sms_aliyun_access_key_id=None,
        auth_sms_aliyun_access_key_secret=None,
        auth_sms_aliyun_sign_name=None,
        auth_sms_aliyun_template_code=None,
        screenshot_vision_base_url=None,
        screenshot_vision_api_key=None,
        realtime_asr_api_key=None,
        integration_mineru_base_url=None,
        integration_mineru_api_key=None,
        document_processing_embedding_provider="synthetic-embedding",
        embedding_base_url=None,
        embedding_api_key=None,
        retrieval_query_embedding_provider="synthetic-query-embedding",
        rerank_base_url=None,
        rerank_api_key=None,
    )


@pytest.fixture(autouse=True)
def clear_dependency_caches():
    for factory in FACTORIES:
        factory.cache_clear()
    yield
    for factory in FACTORIES:
        factory.cache_clear()


def test_production_rejects_explicit_owner_without_authentication(monkeypatch) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: isolated_settings("production"))
    with pytest.raises(DomainRequestError) as error:
        deps.resolve_owned_user_id(explicit_user_id="another-user", auth_context=None)
    assert error.value.status_code == 401


def test_development_keeps_explicit_owner_compatibility(monkeypatch) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: isolated_settings("development"))
    assert deps.resolve_owned_user_id(explicit_user_id="synthetic-user", auth_context=None) == "synthetic-user"


@pytest.mark.parametrize("factory", FACTORIES)
def test_production_provider_factories_fail_closed(monkeypatch, factory) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: isolated_settings("production"))
    with pytest.raises(RuntimeError) as error:
        factory()
    message = str(error.value)
    assert "production" in message


def test_development_provider_factories_keep_synthetic_adapters(monkeypatch) -> None:
    settings = isolated_settings("development")
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    assert isinstance(deps.sms_verification_provider(), FakeSmsVerificationProvider)
    assert isinstance(deps.screenshot_vision_gateway(), SyntheticVisionGateway)
    assert isinstance(deps.realtime_asr_gateway(), SyntheticRealtimeAsrGateway)
    assert isinstance(deps.embedding_adapter(), SyntheticEmbeddingAdapter)
    assert isinstance(deps.query_embedding_adapter(), SyntheticQueryEmbeddingAdapter)
    assert isinstance(deps.reranker_adapter(), HeuristicRerankerAdapter)


def test_production_validation_names_missing_variable_without_secret_value() -> None:
    settings = isolated_settings("production")
    with pytest.raises(RuntimeError) as error:
        deps._require_production_provider(settings, "realtime-asr", {
            "OFFERSTEADY_REALTIME_ASR_API_KEY": None,
            "OFFERSTEADY_OTHER_SECRET": "must-not-appear",
        })
    message = str(error.value)
    assert "OFFERSTEADY_REALTIME_ASR_API_KEY" in message
    assert "must-not-appear" not in message
