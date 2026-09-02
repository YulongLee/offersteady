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
    chat_prompt_version: str = "v4"
    chat_max_history_entries: int = 6
    chat_retry_max_attempts: int = 1
    chat_stream_chunk_chars: int = 32
    chat_quick_max_tokens: int = 420
    chat_detail_max_tokens: int = 1400
    chat_continuation_max_tokens: int = 900
    chat_continuation_max_attempts: int = 2
    chat_detail_retrieval_prefetch_enabled: bool = True
    chat_provider: str = "qwen-compatible"
    chat_qwen_model: str = "qwen-plus"
    chat_qwen_api_key: str | None = None
    chat_qwen_base_url: str | None = None
    chat_http_max_connections: int = 32
    chat_http_max_keepalive_connections: int = 16
    chat_http_keepalive_expiry_seconds: float = 30.0
    screenshot_prompt_template_path: str = "ai/prompts/screenshot-answer/system.md"
    screenshot_prompt_version: str = "v2"
    screenshot_max_history_entries: int = 4
    screenshot_retry_max_attempts: int = 1
    screenshot_max_images_per_task: int = 4
    screenshot_max_file_size_bytes: int = 10 * 1024 * 1024
    screenshot_vision_provider: str = "qwen-vision-compatible"
    screenshot_vision_model: str = "qwen-vl-plus"
    screenshot_vision_delivery_mode: Literal["inline", "oss"] = "inline"
    screenshot_oss_key_prefix: str = "screenshots"
    screenshot_signed_url_ttl_seconds: int = 600
    screenshot_use_signed_url_for_vision: bool = True
    screenshot_optimize_before_vision: bool = True
    screenshot_vision_max_long_edge: int = 1600
    screenshot_vision_jpeg_quality: int = 72
    screenshot_vision_streaming_enabled: bool = True
    screenshot_vision_enable_thinking: bool = False
    screenshot_progress_emit_interval_ms: int = 120
    realtime_publisher_ttl_seconds: int = 1800
    realtime_protocol_version: str = "2.0"
    realtime_transport_mode: str = "websocket-v2"
    realtime_legacy_http_enabled: bool = True
    realtime_ingress_queue_max_frames: int = 64
    realtime_asr_worker_count: int = 8
    realtime_cold_path_worker_count: int = 2
    realtime_cold_path_queue_max: int = 256
    realtime_ingress_max_frames_per_second: int = 120
    realtime_ingress_sequence_gap_max_events: int = 8
    realtime_ingress_coalesce_max_frames: int = 4
    realtime_terminal_admission_timeout_seconds: float = 0.25
    realtime_terminal_ack_enabled: bool = True
    realtime_source_watchdog_enabled: bool = False
    realtime_source_watchdog_seconds: float = 2.5
    realtime_source_watchdog_poll_seconds: float = 0.5
    realtime_event_retention: int = 1000
    realtime_event_block_ms: int = 1000
    realtime_event_wait_workers: int = 32
    realtime_control_worker_count: int = 8
    realtime_control_queue_max: int = 64
    realtime_control_cache_ms: int = 900
    realtime_runtime_ttl_seconds: int = 7200
    live_task_runtime_ttl_seconds: int = 7200
    live_task_stale_seconds: int = 180
    realtime_transcript_persistence_enabled: bool = False
    realtime_transcript_retention_days: int = 30
    realtime_asr_session_idle_seconds: int = 300
    redis_url: str | None = None
    redis_socket_timeout_seconds: float = 2.0
    redis_realtime_required: bool = False
    realtime_redis_snapshot_reload_on_access: bool = False
    realtime_desktop_heartbeat_ttl_seconds: int = 45
    realtime_web_heartbeat_ttl_seconds: int = 60
    interview_idle_warning_seconds: int = 18 * 60
    interview_idle_timeout_seconds: int = 20 * 60
    interview_activity_touch_interval_seconds: int = 15
    interview_idle_reaper_batch_size: int = 100
    realtime_asr_frame_timeout_seconds: float = 12.0
    realtime_asr_partial_timeout_seconds: float = 0.03
    realtime_asr_finalize_timeout_seconds: float = 2.0
    realtime_asr_commit_silence_ms: int = 0
    realtime_asr_retry_max_attempts: int = 1
    realtime_asr_persistent_sessions_enabled: bool = True
    realtime_asr_nonblocking_partials_enabled: bool = True
    realtime_asr_prewarm_enabled: bool = True
    realtime_asr_prewarm_wait_seconds: float = 2.5
    realtime_asr_attachment_prewarm_enabled: bool = True
    realtime_asr_replay_buffer_enabled: bool = True
    realtime_asr_replay_buffer_max_bytes: int = 512 * 1024
    realtime_asr_replay_tail_ms: int = 2_000
    realtime_asr_continuous_task_enabled: bool = False
    realtime_asr_continuous_task_sentence_wait_seconds: float = 0.65
    realtime_asr_points_per_minute: int = 5
    realtime_asr_provider: str = "qwen-realtime-asr-compatible"
    realtime_asr_model: str = "qwen-realtime"
    realtime_asr_protocol: str = "qwen3-realtime"
    realtime_asr_inference_ws_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    realtime_asr_max_sentence_silence_ms: int = 300
    realtime_question_auto_confirm_threshold: float = 0.85
    runtime_performance_telemetry_enabled: bool = True
    runtime_performance_telemetry_ttl_seconds: int = 7 * 24 * 60 * 60
    runtime_performance_telemetry_sample_rate: float = 1.0
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
    auth_sms_code_pepper: str | None = None
    auth_sms_ttl_seconds: int = 300
    auth_sms_send_interval_seconds: int = 60
    auth_sms_daily_limit: int = 20
    auth_sms_verify_attempt_limit: int = 5
    auth_sms_fake_code: str = "123456"
    auth_sms_test_phone_number: str | None = None
    admin_enabled: bool = False
    admin_allowed_origins: list[str] = Field(default_factory=list)
    admin_session_ttl_seconds: int = 8 * 60 * 60
    admin_recent_mfa_ttl_seconds: int = 5 * 60
    admin_session_signing_secret: str | None = None
    admin_encryption_key: str | None = None
    admin_max_page_size: int = 100
    admin_query_timeout_ms: int = 3000
    admin_rate_limit_per_minute: int = 120
    admin_max_concurrent_queries: int = 4
    admin_capacity_sample_interval_seconds: int = 30
    admin_capacity_retention_seconds: int = 6 * 60 * 60
    admin_capacity_active_interviews_warning: int = 10
    admin_capacity_active_interviews_critical: int = 20
    admin_capacity_audio_streams_warning: int = 16
    admin_capacity_audio_streams_critical: int = 32
    admin_capacity_cpu_warning_percent: float = 70.0
    admin_capacity_cpu_critical_percent: float = 90.0
    admin_capacity_memory_warning_percent: float = 75.0
    admin_capacity_memory_critical_percent: float = 90.0
    admin_capacity_api_p95_warning_ms: float = 500.0
    admin_capacity_api_p95_critical_ms: float = 1500.0
    admin_capacity_error_rate_warning_percent: float = 2.0
    admin_capacity_error_rate_critical_percent: float = 5.0

    # Promotion analytics is an isolated, opt-in side path. Keeping collection
    # disabled by default prevents unfinished/local builds from changing live traffic.
    promotion_enabled: bool = False
    promotion_public_base_url: str | None = None
    promotion_safe_fallback_path: str = "/"
    promotion_allowed_destination_prefixes: list[str] = Field(default_factory=lambda: ["/", "/app", "/guide", "/login"])
    promotion_attribution_window_days: int = 30
    promotion_visitor_cookie_days: int = 90
    promotion_touchpoint_retention_days: int = 180
    promotion_reporting_timezone: str = "Asia/Shanghai"
    promotion_model_version: int = 1
    promotion_qualification_min_visible_ms: int = 800
    promotion_redis_stream: str = "offersteady:promotion:events"
    promotion_redis_stream_maxlen: int = 100_000
    promotion_queue_timeout_ms: int = 200
    promotion_ingest_interval_seconds: int = 10
    promotion_visitor_hmac_secret: str = "offersteady-local-promotion-hmac"
    promotion_redirect_rate_limit_per_minute: int = 120
    promotion_qualification_rate_limit_per_minute: int = 30
    promotion_claim_rate_limit_per_minute: int = 20

    public_web_base_url: str = "http://127.0.0.1:5173"
    checkout_provider: str = ""
    mzfpay_base_url: str = "https://pay.mzfpay.com"
    mzfpay_pid: str | None = None
    mzfpay_key: str | None = None
    mzfpay_submit_path: str = "/xpay/epay/submit.php"
    mzfpay_notify_url: str | None = None
    mzfpay_return_url: str | None = None
    mzfpay_payment_ttl_seconds: int = 900
    alipay_gateway_url: str = "https://openapi.alipay.com/gateway.do"
    alipay_app_id: str | None = None
    alipay_app_private_key: str | None = None
    alipay_public_key: str | None = None
    alipay_seller_id: str | None = None
    alipay_notify_url: str | None = None
    alipay_return_url: str | None = None
    alipay_payment_ttl_seconds: int = 900
    wechat_pay_native_url: str = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"
    wechat_pay_mch_id: str | None = None
    wechat_pay_app_id: str | None = None
    wechat_pay_merchant_serial_no: str | None = None
    wechat_pay_merchant_private_key: str | None = None
    wechat_pay_platform_public_key: str | None = None
    wechat_pay_api_v3_key: str | None = None
    wechat_pay_notify_url: str | None = None
    wechat_pay_payment_ttl_seconds: int = 900
    redemption_code_points: dict[str, int] = Field(default_factory=dict)
    redemption_code_pepper: str | None = None
    billing_usage_reservation_ttl_seconds: int = 30 * 60
    support_wechat_id: str = "mianshiwen-cn"
    support_email: str = "contact@oneshowailab.com"
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

    @property
    def resolved_promotion_public_base_url(self) -> str:
        """Use the canonical Web origin unless a dedicated promotion origin is configured."""
        return (self.promotion_public_base_url or self.public_web_base_url).rstrip("/")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
