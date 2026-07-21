from __future__ import annotations

import os
from threading import Lock
from functools import lru_cache
from typing import Callable, TypeVar

from fastapi import Header

from .adapters.oss_storage import AliyunOssStorageAdapter
from .core.config import REPO_ROOT, Settings, get_settings
from .core.errors import DomainRequestError
from .core.logging import configure_logging
from .ports.authentication import AccessTokenCodecPort, AuthenticatedRequestContext, AuthenticationRepository, PasswordHasherPort, SmsVerificationProviderPort
from .ports.commercial_hardening import CommercialHardeningRepository
from .ports.document_processing import ProcessingTaskRepository, VectorStorePort
from .ports.chat import ChatRepository, LLMGatewayPort, PromptBuilderPort, PromptTemplatePort
from .ports.document_repository import DocumentRepository
from .ports.interview_session import InterviewSessionRepository
from .ports.answer_generation import NullAnswerGenerationPort
from .ports.parsing import NullDocumentParsingPort
from .ports.retrieval import RetrievalPort
from .ports.screenshot_analysis import NullScreenshotAnalysisPort
from .ports.screenshot_answer import ScreenshotAnswerRepository, ScreenshotUploadPort, ScreenshotPromptBuilderPort, ScreenshotPromptTemplatePort, VisionGatewayPort
from .ports.realtime_speech import RealtimeAsrGatewayPort, RealtimeSpeechRepository
from .ports.storage import FileStoragePort
from .ports.streaming import NullStreamingPort
from .platform.database import DatabaseRuntime
from .platform.object_storage import ObjectStorageRuntime
from .platform.pgvector import PgvectorRuntime
from .services.document_processing import DocumentProcessingService
from .services.document_processing_adapters import (
    ChunkMetadataBuilderAdapter,
    InMemoryPgvectorStore,
    MarkdownCleanerAdapter,
    MarkdownChunkSplitterAdapter,
    MarkdownNormalizerAdapter,
    MineruDocumentParserAdapter,
    DashScopeCompatibleEmbeddingAdapter,
    SyntheticEmbeddingAdapter,
)
from .services.embedding_pipeline import EmbeddingPipelineService, ProcessingTaskEmbeddingStatusReporter
from .services.document_parser import DocumentParserService, ProcessingTaskParserStatusReporter
from .services.document_processing_repository import InMemoryProcessingTaskRepository
from .services.chat_repository import InMemoryChatRepository
from .services.chat_service import ChatService, FilePromptTemplateAdapter, InterviewPromptBuilder, QwenCompatibleGateway
from .services.authentication_repository import InMemoryAuthenticationRepository
from .services.postgres_authentication_repository import PostgresAuthenticationRepository
from .services.authentication_service import AuthenticationService, CompatibleWechatLoginProvider, JWTAccessTokenCodec, PBKDF2PasswordHasher
from .services.sms_verification_provider import AliyunDypnsSmsVerificationProvider, FakeSmsVerificationProvider
from .services.billing_service import BillingService
from .services.postgres_billing_repository import PostgresBillingRepository
from .services.postgres_points_redemption_repository import PostgresPointsRedemptionRepository
from .services.document_repository import InMemoryDocumentRepository
from .services.postgres_material_persistence import PostgresDocumentRepository, PostgresKnowledgeCollectionStore, PostgresRuntimeVectorStore
from .services.commercial_hardening import InMemoryCommercialHardeningRepository, PostgresCommercialHardeningRepository
from .services.document_service import DocumentService, InMemoryKnowledgeCollectionStore
from .services.material_deletion import InMemoryMaterialDeletionScheduler
from .services.material_availability import MaterialAvailabilityValidator
from .services.interview_session_repository import InMemoryInterviewSessionRepository
from .services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from .services.knowledge_retrieval import (
    DashScopeCompatibleQueryEmbeddingAdapter,
    DashScopeRerankerAdapter,
    HeuristicRerankerAdapter,
    KnowledgeRetrievalService,
    RetrievalContextBuilder,
    SyntheticQueryEmbeddingAdapter,
)
from .services.session_service import SessionService
from .services.screenshot_answer_repository import InMemoryScreenshotAnswerRepository
from .services.screenshot_answer_service import (
    FileScreenshotPromptTemplateAdapter,
    InMemoryScreenshotUploadPort,
    OpenAICompatibleVisionGateway,
    ScreenshotAnswerService,
    ScreenshotPreprocessor,
    ScreenshotPromptBuilder,
    SyntheticVisionGateway,
)
from .services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from .services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
from .services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway
from .services.realtime_speech_service import RealtimeSpeechService, SyntheticRealtimeAsrGateway

import psycopg

_commercial_repository_init_lock = Lock()


class _ReadOnlyNoopStorage:
    def __getattr__(self, name: str):
        raise RuntimeError(f"storage operation {name} is unavailable in read-only web state")


def settings_dependency() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def logger():
    return configure_logging(get_settings())


@lru_cache(maxsize=1)
def storage_port() -> FileStoragePort:
    return AliyunOssStorageAdapter(get_settings())


T = TypeVar("T")


def _fallback_to_memory_repository(*,
    logger_key: str,
    environment: str,
    build_postgres: Callable[[], T],
    fallback: Callable[[], T],
) -> T:
    try:
        return build_postgres()
    except psycopg.OperationalError as exc:
        if environment == "production":
            raise
        logger().warning(
            "fallback_to_in_memory_repository",
            extra={
                "repository": logger_key,
                "error": str(exc),
            },
        )
        return fallback()


def _require_production_provider(settings: Settings, capability: str, required: dict[str, object]) -> None:
    if settings.environment != "production":
        return
    missing = [name for name, value in required.items() if value is None or (isinstance(value, str) and not value.strip())]
    if missing:
        raise RuntimeError(f"{capability} production configuration is incomplete; missing: {', '.join(missing)}")


@lru_cache(maxsize=1)
def document_repository() -> DocumentRepository:
    settings = get_settings()
    if settings.environment == "production" and not settings.database_url:
        raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production material persistence")
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fallback_to_memory_repository(
            logger_key="document_repository",
            environment=settings.environment,
            build_postgres=lambda: PostgresDocumentRepository(settings),
            fallback=lambda: InMemoryDocumentRepository(),
        )
    return InMemoryDocumentRepository()


@lru_cache(maxsize=1)
def knowledge_collection_store() -> InMemoryKnowledgeCollectionStore:
    settings = get_settings()
    if settings.environment == "production" and not settings.database_url:
        raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production knowledge persistence")
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fallback_to_memory_repository(
            logger_key="knowledge_collection_store",
            environment=settings.environment,
            build_postgres=lambda: PostgresKnowledgeCollectionStore(settings),  # type: ignore[return-value]
            fallback=lambda: InMemoryKnowledgeCollectionStore(),
        )
    return InMemoryKnowledgeCollectionStore()


@lru_cache(maxsize=1)
def material_deletion_scheduler() -> InMemoryMaterialDeletionScheduler:
    return InMemoryMaterialDeletionScheduler(settings=get_settings(), storage=storage_port())


@lru_cache(maxsize=1)
def commercial_hardening_repository() -> CommercialHardeningRepository:
    settings = get_settings()
    with _commercial_repository_init_lock:
        if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
            return _fallback_to_memory_repository(
                logger_key="commercial_hardening_repository",
                environment=settings.environment,
                build_postgres=lambda: PostgresCommercialHardeningRepository(settings),
                fallback=lambda: InMemoryCommercialHardeningRepository(),
            )
        return InMemoryCommercialHardeningRepository()


@lru_cache(maxsize=1)
def material_availability_validator() -> MaterialAvailabilityValidator:
    return MaterialAvailabilityValidator(settings=get_settings(), storage=storage_port())


def document_service() -> DocumentService:
    return DocumentService(
        storage=storage_port(),
        repository=document_repository(),
        knowledge_store=knowledge_collection_store(),
        processing_service=document_processing_service(),
        deletion_scheduler=material_deletion_scheduler(),
        commercial_repository=commercial_hardening_repository(),
    )


def document_read_service() -> DocumentService:
    return DocumentService(
        storage=_ReadOnlyNoopStorage(),  # type: ignore[arg-type]
        repository=document_repository(),
        knowledge_store=knowledge_collection_store(),
        processing_service=None,
        deletion_scheduler=None,
        commercial_repository=None,
    )


@lru_cache(maxsize=1)
def interview_session_repository() -> InterviewSessionRepository:
    settings = get_settings()
    if settings.environment == "production" and not settings.database_url:
        raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production interview persistence")
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fallback_to_memory_repository(
            logger_key="interview_session_repository",
            environment=settings.environment,
            build_postgres=lambda: PostgresInterviewSessionRepository(settings),
            fallback=lambda: InMemoryInterviewSessionRepository(),
        )
    return InMemoryInterviewSessionRepository()


@lru_cache(maxsize=1)
def session_service() -> SessionService:
    return SessionService(
        settings=get_settings(),
        document_repository=document_repository(),
        repository=interview_session_repository(),
        material_availability=material_availability_validator(),
    )


@lru_cache(maxsize=1)
def chat_repository() -> ChatRepository:
    return InMemoryChatRepository()


@lru_cache(maxsize=1)
def prompt_template_port() -> PromptTemplatePort:
    return FilePromptTemplateAdapter(get_settings())


@lru_cache(maxsize=1)
def prompt_builder_port() -> PromptBuilderPort:
    return InterviewPromptBuilder()


@lru_cache(maxsize=1)
def llm_gateway_port() -> LLMGatewayPort:
    settings = get_settings()
    _require_production_provider(settings, "chat", {
        "OFFERSTEADY_CHAT_QWEN_BASE_URL": settings.chat_qwen_base_url,
        "OFFERSTEADY_CHAT_QWEN_API_KEY": settings.chat_qwen_api_key,
    })
    return QwenCompatibleGateway(settings)


@lru_cache(maxsize=1)
def chat_service() -> ChatService:
    return ChatService(
        settings=get_settings(),
        logger=logger(),
        session_service=session_service(),
        retrieval_service=retrieval_port(),
        object_storage=storage_port(),
        repository=chat_repository(),
        prompt_template=prompt_template_port(),
        prompt_builder=prompt_builder_port(),
        llm_gateway=llm_gateway_port(),
    )


@lru_cache(maxsize=1)
def authentication_repository() -> AuthenticationRepository:
    settings = get_settings()
    if settings.environment == "production" and not settings.database_url:
        raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production authentication persistence")
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fallback_to_memory_repository(
            logger_key="authentication_repository",
            environment=settings.environment,
            build_postgres=lambda: PostgresAuthenticationRepository(settings),
            fallback=lambda: InMemoryAuthenticationRepository(),
        )
    return InMemoryAuthenticationRepository()


@lru_cache(maxsize=1)
def password_hasher_port() -> PasswordHasherPort:
    return PBKDF2PasswordHasher(get_settings())


@lru_cache(maxsize=1)
def access_token_codec_port() -> AccessTokenCodecPort:
    return JWTAccessTokenCodec(get_settings())


@lru_cache(maxsize=1)
def wechat_login_provider():
    return CompatibleWechatLoginProvider(get_settings())


@lru_cache(maxsize=1)
def sms_verification_provider() -> SmsVerificationProviderPort:
    settings = get_settings()
    if settings.auth_sms_provider_mode == "aliyun":
        _require_production_provider(settings, "sms", {
            "OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_ID": settings.auth_sms_aliyun_access_key_id,
            "OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_SECRET": settings.auth_sms_aliyun_access_key_secret,
            "OFFERSTEADY_AUTH_SMS_ALIYUN_SIGN_NAME": settings.auth_sms_aliyun_sign_name,
            "OFFERSTEADY_AUTH_SMS_ALIYUN_TEMPLATE_CODE": settings.auth_sms_aliyun_template_code,
        })
        return AliyunDypnsSmsVerificationProvider(settings)
    if settings.environment == "production":
        raise RuntimeError("sms production configuration requires OFFERSTEADY_AUTH_SMS_PROVIDER_MODE=aliyun")
    return FakeSmsVerificationProvider(settings)


@lru_cache(maxsize=1)
def authentication_service() -> AuthenticationService:
    return AuthenticationService(
        settings=get_settings(),
        logger=logger(),
        repository=authentication_repository(),
        password_hasher=password_hasher_port(),
        token_codec=access_token_codec_port(),
        wechat_provider=wechat_login_provider(),
        sms_provider=sms_verification_provider(),
    )


@lru_cache(maxsize=1)
def billing_service() -> BillingService:
    settings = get_settings()
    if settings.environment == "production" and not settings.database_url:
        raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production billing persistence")
    if settings.environment == "production" and settings.redemption_code_points:
        if not settings.database_url:
            raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for production redemption persistence")
        if not settings.redemption_code_pepper:
            raise RuntimeError("OFFERSTEADY_REDEMPTION_CODE_PEPPER is required for production redemption persistence")
    repository = None
    if settings.database_url and settings.redemption_code_pepper and not os.environ.get("PYTEST_CURRENT_TEST"):
        repository = _fallback_to_memory_repository(
            logger_key="points_redemption_repository",
            environment=settings.environment,
            build_postgres=lambda: PostgresPointsRedemptionRepository(settings),
            fallback=lambda: None,
        )
    billing_repository = None
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        billing_repository = _fallback_to_memory_repository(
            logger_key="billing_repository",
            environment=settings.environment,
            build_postgres=lambda: PostgresBillingRepository(settings),
            fallback=lambda: None,
        )
    return BillingService(settings, redemption_repository=repository, billing_repository=billing_repository)


@lru_cache(maxsize=1)
def screenshot_answer_repository() -> ScreenshotAnswerRepository:
    return InMemoryScreenshotAnswerRepository()


@lru_cache(maxsize=1)
def screenshot_upload_port() -> ScreenshotUploadPort:
    return InMemoryScreenshotUploadPort(get_settings())


@lru_cache(maxsize=1)
def screenshot_preprocessor() -> ScreenshotPreprocessor:
    return ScreenshotPreprocessor()


@lru_cache(maxsize=1)
def screenshot_vision_gateway() -> VisionGatewayPort:
    settings = get_settings()
    _require_production_provider(settings, "screenshot-vision", {
        "OFFERSTEADY_SCREENSHOT_VISION_BASE_URL": settings.screenshot_vision_base_url,
        "OFFERSTEADY_SCREENSHOT_VISION_API_KEY": settings.screenshot_vision_api_key,
    })
    if settings.screenshot_vision_base_url and settings.screenshot_vision_api_key and (
        not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_SCREENSHOT_VISION") == "1"
    ):
        return OpenAICompatibleVisionGateway(settings)
    return SyntheticVisionGateway(get_settings())


@lru_cache(maxsize=1)
def screenshot_prompt_template_port() -> ScreenshotPromptTemplatePort:
    return FileScreenshotPromptTemplateAdapter(get_settings())


@lru_cache(maxsize=1)
def screenshot_prompt_builder_port() -> ScreenshotPromptBuilderPort:
    return ScreenshotPromptBuilder()


@lru_cache(maxsize=1)
def screenshot_answer_service() -> ScreenshotAnswerService:
    return ScreenshotAnswerService(
        settings=get_settings(),
        logger=logger(),
        session_service=session_service(),
        retrieval_service=retrieval_port(),
        object_storage=storage_port(),
        repository=screenshot_answer_repository(),
        upload_port=screenshot_upload_port(),
        preprocessor=screenshot_preprocessor(),
        vision_gateway=screenshot_vision_gateway(),
        prompt_template=screenshot_prompt_template_port(),
        prompt_builder=screenshot_prompt_builder_port(),
        llm_gateway=llm_gateway_port(),
    )


@lru_cache(maxsize=1)
def realtime_speech_repository() -> RealtimeSpeechRepository:
    settings = get_settings()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return InMemoryRealtimeSpeechRepository()
    if settings.redis_url:
        try:
            return RedisRealtimeSpeechRepository(settings)
        except Exception:
            if settings.environment == "production" or settings.redis_realtime_required:
                raise
            logger().warning("realtime_redis_unavailable_falling_back_to_local_state")
    state_file = settings.realtime_speech_state_file
    if not os.path.isabs(state_file):
        state_file = str((REPO_ROOT / state_file).resolve())
    return InMemoryRealtimeSpeechRepository(state_file=state_file)


@lru_cache(maxsize=1)
def realtime_asr_gateway() -> RealtimeAsrGatewayPort:
    settings = get_settings()
    _require_production_provider(settings, "realtime-asr", {
        "OFFERSTEADY_REALTIME_ASR_API_KEY": settings.realtime_asr_api_key,
    })
    if settings.realtime_asr_api_key and (not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_REALTIME_ASR") == "1"):
        return DashScopeRealtimeAsrGateway(settings, logger())
    return SyntheticRealtimeAsrGateway(settings)


@lru_cache(maxsize=1)
def realtime_speech_service() -> RealtimeSpeechService:
    return RealtimeSpeechService(
        settings=get_settings(),
        logger=logger(),
        repository=realtime_speech_repository(),
        session_service=session_service(),
        chat_service=chat_service(),
        asr_gateway=realtime_asr_gateway(),
    )


@lru_cache(maxsize=1)
def processing_task_repository() -> ProcessingTaskRepository:
    return InMemoryProcessingTaskRepository()


@lru_cache(maxsize=1)
def document_parser_adapter() -> MineruDocumentParserAdapter:
    settings = get_settings()
    _require_production_provider(settings, "mineru", {
        "OFFERSTEADY_INTEGRATION_MINERU_BASE_URL": settings.integration_mineru_base_url,
        "OFFERSTEADY_INTEGRATION_MINERU_API_KEY": settings.integration_mineru_api_key,
    })
    return MineruDocumentParserAdapter(settings)


@lru_cache(maxsize=1)
def markdown_normalizer_adapter() -> MarkdownNormalizerAdapter:
    return MarkdownNormalizerAdapter()


@lru_cache(maxsize=1)
def chunk_splitter_adapter() -> MarkdownChunkSplitterAdapter:
    return MarkdownChunkSplitterAdapter()


@lru_cache(maxsize=1)
def markdown_cleaner_adapter() -> MarkdownCleanerAdapter:
    return MarkdownCleanerAdapter()


@lru_cache(maxsize=1)
def chunk_metadata_builder_adapter() -> ChunkMetadataBuilderAdapter:
    return ChunkMetadataBuilderAdapter()


@lru_cache(maxsize=1)
def embedding_adapter() -> SyntheticEmbeddingAdapter:
    settings = get_settings()
    _require_production_provider(settings, "embedding", {
        "OFFERSTEADY_EMBEDDING_BASE_URL": settings.embedding_base_url,
        "OFFERSTEADY_EMBEDDING_API_KEY": settings.embedding_api_key,
    })
    if settings.embedding_base_url and settings.embedding_api_key and (not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_EMBEDDING") == "1"):
        return DashScopeCompatibleEmbeddingAdapter(settings)  # type: ignore[return-value]
    return SyntheticEmbeddingAdapter(get_settings())


@lru_cache(maxsize=1)
def vector_store_adapter() -> VectorStorePort:
    settings = get_settings()
    if settings.database_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fallback_to_memory_repository(
            logger_key="vector_store",
            environment=settings.environment,
            build_postgres=lambda: PostgresRuntimeVectorStore(settings),
            fallback=lambda: InMemoryPgvectorStore(),
        )
    return InMemoryPgvectorStore()


@lru_cache(maxsize=1)
def query_embedding_adapter() -> SyntheticQueryEmbeddingAdapter:
    settings = get_settings()
    _require_production_provider(settings, "query-embedding", {
        "OFFERSTEADY_EMBEDDING_BASE_URL": settings.embedding_base_url,
        "OFFERSTEADY_EMBEDDING_API_KEY": settings.embedding_api_key,
    })
    if settings.embedding_base_url and settings.embedding_api_key and (not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_EMBEDDING") == "1"):
        return DashScopeCompatibleQueryEmbeddingAdapter(settings)  # type: ignore[return-value]
    return SyntheticQueryEmbeddingAdapter(get_settings())


@lru_cache(maxsize=1)
def reranker_adapter() -> HeuristicRerankerAdapter:
    settings = get_settings()
    _require_production_provider(settings, "rerank", {
        "OFFERSTEADY_RERANK_BASE_URL": settings.rerank_base_url,
        "OFFERSTEADY_RERANK_API_KEY": settings.rerank_api_key,
    })
    if settings.rerank_base_url and settings.rerank_api_key and (not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OFFERSTEADY_TEST_USE_REMOTE_RERANK") == "1"):
        return DashScopeRerankerAdapter(settings)  # type: ignore[return-value]
    return HeuristicRerankerAdapter()


@lru_cache(maxsize=1)
def retrieval_context_builder() -> RetrievalContextBuilder:
    return RetrievalContextBuilder()


@lru_cache(maxsize=1)
def parser_status_reporter() -> ProcessingTaskParserStatusReporter:
    return ProcessingTaskParserStatusReporter(settings=get_settings(), logger=logger(), task_repository=processing_task_repository())


@lru_cache(maxsize=1)
def embedding_status_reporter() -> ProcessingTaskEmbeddingStatusReporter:
    return ProcessingTaskEmbeddingStatusReporter(settings=get_settings(), logger=logger(), task_repository=processing_task_repository())


@lru_cache(maxsize=1)
def document_parser_service() -> DocumentParserService:
    return DocumentParserService(
        settings=get_settings(),
        logger=logger(),
        object_storage=storage_port(),
        binary_parser=document_parser_adapter(),
        markdown_normalizer=markdown_normalizer_adapter(),
        status_reporter=parser_status_reporter(),
        commercial_repository=commercial_hardening_repository(),
    )


@lru_cache(maxsize=1)
def embedding_pipeline_service() -> EmbeddingPipelineService:
    return EmbeddingPipelineService(
        settings=get_settings(),
        logger=logger(),
        cleaner=markdown_cleaner_adapter(),
        splitter=chunk_splitter_adapter(),
        metadata_builder=chunk_metadata_builder_adapter(),
        embedding=embedding_adapter(),
        vector_store=vector_store_adapter(),
        status_reporter=embedding_status_reporter(),
        artifact_storage=storage_port(),
        commercial_repository=commercial_hardening_repository(),
    )


@lru_cache(maxsize=1)
def document_processing_service() -> DocumentProcessingService:
    return DocumentProcessingService(
        settings=get_settings(),
        logger=logger(),
        document_repository=document_repository(),
        task_repository=processing_task_repository(),
        parser_service=document_parser_service(),
        embedding_pipeline=embedding_pipeline_service(),
        material_availability=material_availability_validator(),
        commercial_repository=commercial_hardening_repository(),
    )


def parsing_port() -> NullDocumentParsingPort:
    return NullDocumentParsingPort()


@lru_cache(maxsize=1)
def retrieval_port() -> RetrievalPort:
    return KnowledgeRetrievalService(
        settings=get_settings(),
        logger=logger(),
        query_embedding=query_embedding_adapter(),
        vector_store=vector_store_adapter(),
        document_repository=document_repository(),
        reranker=reranker_adapter(),
        context_builder=retrieval_context_builder(),
        commercial_repository=commercial_hardening_repository(),
    )


@lru_cache(maxsize=1)
def database_runtime() -> DatabaseRuntime:
    return DatabaseRuntime(get_settings())


@lru_cache(maxsize=1)
def pgvector_runtime() -> PgvectorRuntime:
    return PgvectorRuntime(get_settings())


@lru_cache(maxsize=1)
def object_storage_runtime() -> ObjectStorageRuntime:
    return ObjectStorageRuntime(get_settings())


def answer_generation_port() -> NullAnswerGenerationPort:
    return NullAnswerGenerationPort()


def screenshot_analysis_port() -> NullScreenshotAnalysisPort:
    return NullScreenshotAnalysisPort()


def streaming_port() -> NullStreamingPort:
    return NullStreamingPort()


def require_authenticated_context(authorization: str | None = Header(default=None)) -> AuthenticatedRequestContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise DomainRequestError("authentication", "require-auth", "缺少有效的 Bearer 访问令牌。", 401)
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise DomainRequestError("authentication", "require-auth", "缺少有效的 Bearer 访问令牌。", 401)
    return authentication_service().authenticate_access_token(access_token=token)


def optional_authenticated_context(authorization: str | None = Header(default=None)) -> AuthenticatedRequestContext | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        raise DomainRequestError("authentication", "require-auth", "缺少有效的 Bearer 访问令牌。", 401)
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise DomainRequestError("authentication", "require-auth", "缺少有效的 Bearer 访问令牌。", 401)
    return authentication_service().authenticate_access_token(access_token=token)


def resolve_owned_user_id(*, explicit_user_id: str | None, auth_context: AuthenticatedRequestContext | None) -> str:
    if auth_context is None:
        if get_settings().environment == "production":
            raise DomainRequestError("authentication", "resolve-owner", "请先登录后再继续操作。", 401)
        if explicit_user_id is None or not explicit_user_id.strip():
            raise DomainRequestError("authentication", "resolve-owner", "缺少用户身份。", 401)
        return explicit_user_id
    if explicit_user_id and explicit_user_id != auth_context.user_id:
        raise DomainRequestError("authentication", "resolve-owner", "请求中的用户身份与当前登录态不一致。", 403)
    return auth_context.user_id
