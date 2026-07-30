from __future__ import annotations

import os


# Automated tests use synthetic providers unless a test run explicitly opts into
# a remote integration. This prevents a developer's local .env from turning
# deterministic unit tests into slow, billable network calls.
_REMOTE_PROVIDER_KEYS = {
    "OFFERSTEADY_TEST_USE_REMOTE_CHAT": (
        "OFFERSTEADY_CHAT_QWEN_API_KEY",
    ),
    "OFFERSTEADY_TEST_USE_REMOTE_EMBEDDING": (
        "OFFERSTEADY_EMBEDDING_API_KEY",
    ),
    "OFFERSTEADY_TEST_USE_REMOTE_RERANK": (
        "OFFERSTEADY_RERANK_API_KEY",
    ),
    "OFFERSTEADY_TEST_USE_REMOTE_SCREENSHOT_VISION": (
        "OFFERSTEADY_SCREENSHOT_VISION_API_KEY",
    ),
    "OFFERSTEADY_TEST_USE_REMOTE_REALTIME_ASR": (
        "OFFERSTEADY_REALTIME_ASR_API_KEY",
    ),
}

for opt_in, provider_keys in _REMOTE_PROVIDER_KEYS.items():
    if os.environ.get(opt_in) != "1":
        for provider_key in provider_keys:
            os.environ[provider_key] = ""

os.environ.setdefault("OFFERSTEADY_ENV", "development")
os.environ.setdefault("OFFERSTEADY_AUTH_SMS_PROVIDER_MODE", "fake")
