"""Run the approved mock fixes on loopback, with an isolated synthetic account.

Provider credentials stay in the local backend process. Production databases,
OSS buckets, identity stores and billing data are never loaded by this runner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from time import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/backend"))

from dotenv import dotenv_values
from app.core import config


def local_settings() -> config.Settings:
    # Read only model connection credentials, never a complete production env.
    source = {**dotenv_values(ROOT / ".env.production"), **dotenv_values(ROOT / ".env")}
    names = (
        "chat_qwen_api_key", "chat_qwen_base_url", "realtime_asr_api_key",
        "realtime_asr_ws_url", "realtime_asr_model", "realtime_asr_protocol",
        "mock_interview_tts_api_key", "mock_interview_tts_ws_url",
    )
    providers = {
        name: source[f"OFFERSTEADY_{name.upper()}"]
        for name in names if source.get(f"OFFERSTEADY_{name.upper()}")
    }
    return config.Settings(
        _env_file=None,
        environment="test",
        product_edition="cn",
        app_version="mock-local-20261015.1",
        database_url="postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/local_mock_preview",
        redis_url="redis://127.0.0.1:56385/0",
        mock_interview_enabled=True,
        global_mock_interview_enabled=False,
        chat_qwen_model="deepseek-v4.1-flash",
        mock_interview_tts_model="qwen-audio-3.0-tts-plus",
        mock_interview_tts_voice="longanhuan_v3.6",
        auth_sms_provider_mode="fake",
        auth_sms_fake_code="123456",
        auth_sms_send_interval_seconds=0,
        auth_jwt_secret="synthetic-loopback-mock-preview-20261015",
        oss_bucket=None,
        oss_endpoint=None,
        oss_access_key_id=None,
        oss_access_key_secret=None,
        document_processing_inline_worker_enabled=False,
        realtime_speech_state_file=str(ROOT / "artifacts/mock-local-20261015/realtime-state.json"),
        **providers,
    )


def seed_preview(settings: config.Settings) -> None:
    from app.deps import authentication_service, billing_service, document_repository, storage_port
    from app.ports.document_repository import DocumentRecord
    from app.services.material_object_keys import MaterialObjectKeyFactory

    # Fake SMS login maps this synthetic number to the same local account.
    auth = authentication_service()
    user = auth._get_or_create_sms_user(phone_e164="+8619900000001")
    billing = billing_service()
    billing.state_for_user(user_id=user.user_id)
    order = billing.create_checkout_order(
        user_id=user.user_id, product_id="pass-7", channel="alipay",
        idempotency_key="synthetic-local-preview-pass",
        payment_url="http://127.0.0.1:5175/app", expires_at_ms=int(time() * 1000) + 86_400_000,
    )
    # Local ledger only: no payment provider is called.
    billing.confirm_checkout_paid(
        order_id=order.id, amount_cents=order.amount_cents,
        provider_trade_no=f"synthetic-local-preview-pass-{user.user_id}",
    )
    body = (
        "# 合成练习简历\n\n"
        "这是一份本地测试用合成简历，不含真实个人信息。\n"
        "目标岗位：后端开发工程师。\n"
        "技能：Python、FastAPI、PostgreSQL、Redis，熟悉接口幂等与并发控制。\n"
        "练习项目：设计任务处理服务，使用唯一约束防止重复提交，"
        "以独立任务队列处理慢操作，并记录阶段耗时定位延迟。\n"
    ).encode()
    now = int(time() * 1000)
    document_id, version_id = "synthetic-local-preview-resume", "synthetic-local-preview-v1"
    keys = MaterialObjectKeyFactory(settings)
    key = keys.processed_artifact_key(
        owner_user_id=user.user_id, document_kind="resume", document_id=document_id,
        document_version_id=version_id, artifact_kind="normalized_markdown",
    )
    storage_port().save_object_bytes(object_key=key, payload=body, content_type="text/markdown")
    document_repository().save(DocumentRecord(
        document_id=document_id, owner_user_id=user.user_id, document_kind="resume",
        display_name="本地合成练习简历", file_kind="txt", content_type="text/plain",
        size_bytes=len(body), object_key=key, status="ready", knowledge_collection_id=None,
        processing_requested_at_ms=None, deleted_at_ms=None, created_at_ms=now,
        updated_at_ms=now, summary="合成后端开发练习资料", object_id="synthetic-local-object",
        document_version_id=version_id, version=1, original_filename="synthetic-resume.txt",
        index_state="indexed",
    ))
    print(json.dumps({
        "preview": "http://127.0.0.1:5175/app/mock-interviews",
        "synthetic_login": "19900000001", "fake_sms_code": "123456",
        "chat_configured": bool(settings.chat_qwen_api_key),
        "asr_configured": bool(settings.realtime_asr_api_key),
        "local_database": "local_mock_preview", "synthetic_resume_ready": True,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    settings = local_settings()
    # Supply this explicit instance before importing any cached dependency.
    config.get_settings = lambda: settings
    from app import deps
    from app.services.authentication_repository import InMemoryAuthenticationRepository
    # Synthetic SMS identities live only in this local process. The preview
    # does not exercise or alter production authentication persistence.
    preview_auth = InMemoryAuthenticationRepository()
    deps.authentication_repository = lambda: preview_auth
    from app.main import app
    seed_preview(settings)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8015, log_level="info")
