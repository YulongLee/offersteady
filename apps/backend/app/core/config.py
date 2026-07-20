from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


AppEnvironment = Literal["development", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OFFERSTEADY_",
        env_file=(REPO_ROOT / ".env", REPO_ROOT / ".env.local", ".env", ".env.local"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "OfferSteady Backend"
    app_version: str = "0.1.0"
    environment: AppEnvironment = "development"
    app_mode: str = "foundation"
    prototype_mode: str = "placeholder"
    development_user_id: str = "admin"
    development_user_display_name: str = "admin"
    api_prefix: str = "/api/v1"
    cors_allowed_origins: list[str] = Field(default_factory=lambda: [
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "null",
    ])

    log_level: LogLevel = "INFO"
    log_json: bool = True
    request_id_header: str = "X-Request-Id"

    database_url: str | None = None
    database_echo: bool = False
    database_pool_size: int = 5
    database_pool_max_overflow: int = 10
    database_connect_timeout_seconds: float = 3.0
    database_application_name: str = "offersteady-backend"

    pgvector_schema: str = "public"
    pgvector_extension_name: str = "vector"

    oss_bucket: str | None = None
    oss_endpoint: str | None = None
    oss_region: str | None = None
    oss_key_prefix: str = "materials"
    oss_environment_label: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    oss_upload_intent_ttl_seconds: int = 900
    desktop_release_download_ttl_seconds: int = 600

    material_max_file_size_bytes: int = 50 * 1024 * 1024
    material_max_page_count: int = 50
    material_max_text_characters: int = 500_000
    material_supported_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".doc", ".txt", ".md"])
    material_processing_timeout_seconds: int = 300
    material_indexing_timeout_seconds: int = 300
    material_deletion_grace_seconds: int = 0
    material_object_id_bytes: int = 16
    material_user_hash_salt: str = "offersteady-local-material-path-salt"

    document_processing_parser_provider: str = "mineru"
    document_processing_embedding_provider: str = "synthetic-embedding"
    document_processing_chunk_size: int = 1200
    document_processing_chunk_overlap: int = 120
    embedding_pipeline_batch_size: int = 4
    embedding_pipeline_resume_chunk_size: int = 900
    embedding_pipeline_resume_chunk_overlap: int = 90
    embedding_pipeline_job_description_chunk_size: int = 1000
    embedding_pipeline_job_description_chunk_overlap: int = 120
    embedding_pipeline_knowledge_chunk_size: int = 1400
    embedding_pipeline_knowledge_chunk_overlap: int = 180
    document_processing_max_retries: int = 2
    document_processing_retry_backoff_ms: int = 200
    retrieval_query_embedding_provider: str = "synthetic-query-embedding"
    retrieval_candidate_top_k: int = 6
    retrieval_final_top_k: int = 3
    retrieval_min_score_threshold: float = 0.0
    retrieval_reranker_enabled: bool = True
    retrieval_strategy: str = "filtered-first"
    chat_prompt_template_path: str = "ai/prompts/chat-service/system.md"
    chat_prompt_version: str = "v3"
    chat_max_history_entries: int = 6
    chat_retry_max_attempts: int = 1
    chat_stream_chunk_chars: int = 32
    chat_provider: str = "qwen-compatible"
    chat_qwen_model: str = "qwen-plus"
    chat_qwen_api_key: str | None = None
    chat_qwen_base_url: str | None = None
    screenshot_prompt_template_path: str = "ai/prompts/screenshot-answer/system.md"
    screenshot_prompt_version: str = "v1"
    screenshot_max_history_entries: int = 4
    screenshot_retry_max_attempts: int = 1
    screenshot_max_images_per_task: int = 4
    screenshot_max_file_size_bytes: int = 10 * 1024 * 1024
    screenshot_vision_provider: str = "qwen-vision-compatible"
    screenshot_vision_model: str = "qwen-vl-plus"
    screenshot_oss_key_prefix: str = "screenshots"
    screenshot_signed_url_ttl_seconds: int = 600
    screenshot_use_signed_url_for_vision: bool = True
    screenshot_optimize_before_vision: bool = True
    screenshot_vision_max_long_edge: int = 1600
    screenshot_vision_jpeg_quality: int = 72
    realtime_publisher_ttl_seconds: int = 1800
    realtime_protocol_version: str = "2.0"
    realtime_transport_mode: str = "websocket-v2"
    realtime_legacy_http_enabled: bool = True
    realtime_ingress_queue_max_frames: int = 64
    realtime_ingress_max_frames_per_second: int = 120
    realtime_event_retention: int = 1000
    realtime_runtime_ttl_seconds: int = 7200
    realtime_transcript_persistence_enabled: bool = False
    realtime_transcript_retention_days: int = 30
    realtime_asr_session_idle_seconds: int = 180
    redis_url: str | None = None
    redis_socket_timeout_seconds: float = 2.0
    redis_realtime_required: bool = False
    realtime_desktop_heartbeat_ttl_seconds: int = 45
    realtime_web_heartbeat_ttl_seconds: int = 60
    realtime_asr_frame_timeout_seconds: float = 12.0
    realtime_asr_partial_timeout_seconds: float = 0.08
    realtime_asr_finalize_timeout_seconds: float = 8.0
    realtime_asr_retry_max_attempts: int = 1
    realtime_asr_provider: str = "qwen-realtime-asr-compatible"
    realtime_asr_model: str = "qwen-realtime"
    realtime_question_auto_confirm_threshold: float = 0.85
    auth_jwt_secret: str = "offersteady-dev-jwt-secret"
    auth_jwt_issuer: str = "offersteady-backend"
    auth_access_token_ttl_seconds: int = 900
    auth_refresh_token_ttl_seconds: int = 14 * 24 * 60 * 60
    auth_password_hash_iterations: int = 120000
    auth_wechat_provider_mode: str = "compatible"
    auth_wechat_app_id: str = "offersteady-dev-wechat-app"
    auth_wechat_callback_url: str = "http://127.0.0.1:8000/api/v1/auth/wechat/callback"
    auth_wechat_authorization_ttl_seconds: int = 300
    auth_wechat_app_secret: str | None = None
    auth_sms_provider_mode: str = "fake"
    auth_sms_aliyun_endpoint: str = "https://dypnsapi.aliyuncs.com"
    auth_sms_aliyun_region_id: str = "cn-hangzhou"
    auth_sms_aliyun_access_key_id: str | None = None
    auth_sms_aliyun_access_key_secret: str | None = None
    auth_sms_aliyun_sign_name: str | None = None
    auth_sms_aliyun_template_code: str | None = None
    auth_sms_ttl_seconds: int = 300
    auth_sms_send_interval_seconds: int = 30
    auth_sms_daily_limit: int = 20
    auth_sms_verify_attempt_limit: int = 5
    auth_sms_fake_code: str = "123456"
    auth_sms_test_phone_number: str | None = None

    public_web_base_url: str = "http://127.0.0.1:5173"
    mzfpay_base_url: str = "https://pay.mzfpay.com"
    mzfpay_pid: str | None = None
    mzfpay_key: str | None = None
    mzfpay_submit_path: str = "/xpay/epay/submit.php"
    mzfpay_notify_url: str | None = None
    mzfpay_return_url: str | None = None
    mzfpay_payment_ttl_seconds: int = 900
    redemption_code_points: dict[str, int] = Field(default_factory=dict)
    realtime_speech_state_file: str = "artifacts/runtime/realtime-speech-state.json"

    integration_environment_label: str = "local"
    integration_report_output_dir: str = "artifacts/integration-reports"
    integration_http_timeout_seconds: float = 20.0
    integration_retry_attempts: int = 1
    integration_realtime_asr_protocol: str = "openai-compatible"

    integration_mineru_base_url: str | None = None
    integration_mineru_api_key: str | None = None
    integration_mineru_parse_path: str = "/parse"
    integration_mineru_result_path: str = "/api/v4/extract/task/{task_id}"
    integration_mineru_markdown_field: str = "data.markdown"
    integration_mineru_status_field: str = "data.state"
    integration_mineru_task_id_field: str = "data.task_id"
    integration_mineru_poll_attempts: int = 60
    integration_mineru_poll_interval_ms: int = 2000

    screenshot_vision_base_url: str | None = None
    screenshot_vision_api_key: str | None = None

    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = 1536

    rerank_api_key: str | None = None
    rerank_base_url: str | None = None
    rerank_model: str = "gte-rerank-v2"
    rerank_api_path: str = "/rerank"
    rag_context_max_chunks: int = 6
    rag_context_max_characters: int = 6000
    rag_context_allow_full_document: bool = False

    realtime_asr_api_key: str | None = None
    realtime_asr_base_url: str | None = None
    realtime_asr_ws_url: str | None = None
    realtime_asr_workspace_id: str | None = None
    realtime_asr_workspace_region: str = "cn-beijing"
    realtime_asr_turn_detection_mode: str = "manual"
    realtime_asr_turn_detection_threshold: float = 0.2
    realtime_asr_turn_detection_silence_duration_ms: int = 800
    realtime_asr_connect_timeout_seconds: float = 8.0
    

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
