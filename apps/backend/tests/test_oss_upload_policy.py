from __future__ import annotations

import base64
import json
from datetime import datetime

from app.adapters.oss_storage import AliyunOssStorageAdapter
from app.core.config import Settings


def _adapter(endpoint: str) -> AliyunOssStorageAdapter:
    return AliyunOssStorageAdapter(
        Settings(
            _env_file=None,
            environment="test",
            oss_endpoint=endpoint,
            oss_bucket="projects-yulong",
            oss_access_key_id="test-key",
            oss_access_key_secret="test-secret",
        )
    )


def test_upload_url_uses_aliyun_bucket_subdomain() -> None:
    assert _adapter("https://oss-cn-shanghai.aliyuncs.com")._upload_url() == (
        "https://projects-yulong.oss-cn-shanghai.aliyuncs.com"
    )


def test_upload_url_preserves_bucket_and_custom_domains() -> None:
    assert _adapter("projects-yulong.oss-cn-shanghai.aliyuncs.com")._upload_url() == (
        "https://projects-yulong.oss-cn-shanghai.aliyuncs.com"
    )
    assert _adapter("https://uploads.example.com/path")._upload_url() == "https://uploads.example.com"


def test_post_policy_uses_iso_8601_expiration() -> None:
    encoded, _ = _adapter("https://oss-cn-shanghai.aliyuncs.com")._sign_policy(
        key="materials/user/resume.txt",
        content_type="text/plain",
        expires_at_ms=1_800_000_000_123,
    )
    policy = json.loads(base64.b64decode(encoded))

    assert policy["expiration"].endswith("Z")
    assert datetime.fromisoformat(policy["expiration"].replace("Z", "+00:00")).timestamp() == 1_800_000_000.123
