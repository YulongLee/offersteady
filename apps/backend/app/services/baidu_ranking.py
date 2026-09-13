from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from time import monotonic, time
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

import httpx

from app.core.config import Settings, get_settings
from app.services.admin_repository import AdminRepository, now_ms


def _canonical(value: str) -> str:
    return quote(str(value), safe="-_.~")


def _bce_signature(method: str, url: str, body: str, access_key: str, secret_key: str) -> str:
    parts = urlsplit(url)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expiration = "1800"
    signed_headers = "host;content-type"
    canonical_headers = f"content-type:application%2Fx-www-form-urlencoded\nhost:{_canonical(parts.netloc)}"
    canonical_request = "\n".join([method.upper(), _canonical(parts.path or "/"), "", canonical_headers])
    signing_key = hmac.new(secret_key.encode(), f"bce-auth-v1/{access_key}/{timestamp}/{expiration}".encode(), hashlib.sha256).hexdigest()
    signature = hmac.new(signing_key.encode(), canonical_request.encode(), hashlib.sha256).hexdigest()
    return f"bce-auth-v1/{access_key}/{timestamp}/{expiration}/{signed_headers}/{signature}"


class BaiduRankingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def query(self, *, domain: str, keyword: str) -> dict[str, Any]:
        if not self.settings.baidu_ranking_enabled:
            return {"status": "invalid_config", "safe_error_code": "provider_disabled", "results": []}
        if not self.settings.baidu_ranking_endpoint or not domain.strip() or not keyword.strip():
            return {"status": "invalid_config", "safe_error_code": "missing_config", "results": []}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.settings.baidu_ranking_access_key and self.settings.baidu_ranking_secret_key:
            headers["X-Bce-Signature"] = _bce_signature("POST", self.settings.baidu_ranking_endpoint, "", self.settings.baidu_ranking_access_key, self.settings.baidu_ranking_secret_key)
        elif self.settings.baidu_ranking_app_code:
            headers["X-Bce-Signature"] = f"AppCode/{self.settings.baidu_ranking_app_code}"
        else:
            return {"status": "invalid_config", "safe_error_code": "missing_credentials", "results": []}
        started = monotonic()
        attempts = max(0, int(self.settings.baidu_ranking_retry_attempts)) + 1
        last_error = "provider_error"
        for attempt in range(attempts):
            try:
                response = httpx.post(self.settings.baidu_ranking_endpoint, data={"domain": domain, "keyword": keyword}, headers=headers, timeout=self.settings.baidu_ranking_timeout_seconds)
                duration = int((monotonic() - started) * 1000)
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data") if isinstance(payload, dict) else {}
                raw = data.get("Ranks", []) if isinstance(data, dict) else []
                results = []
                for index, item in enumerate(raw[:50], start=1):
                    if not isinstance(item, dict):
                        continue
                    rank_text = str(item.get("RankStr") or item.get("rank") or index)
                    try:
                        rank = int(rank_text.split("-")[-1])
                    except ValueError:
                        rank = index
                    results.append({"rank": rank, "title": str(item.get("Title") or item.get("title") or ""), "url": str(item.get("Url") or item.get("url") or "")})
                return {"status": "ranked" if results else "not_found", "results": results, "top_rank": results[0]["rank"] if results else None, "matched_url": results[0]["url"] if results else None, "matched_title": results[0]["title"] if results else None, "duration_ms": duration, "safe_error_code": None}
            except httpx.TimeoutException:
                last_error = "timeout"
            except Exception:
                last_error = "provider_error"
            if attempt < attempts - 1:
                continue
        return {"status": last_error, "safe_error_code": last_error, "results": [], "duration_ms": int((monotonic() - started) * 1000)}


class BaiduRankingService:
    def __init__(self, settings: Settings, repository: AdminRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.client = BaiduRankingClient(settings)

    def seed_default_keywords(self) -> None:
        for keyword in self.settings.baidu_ranking_keywords:
            text = str(keyword).strip()
            if text:
                self.repository.upsert_baidu_keyword(domain=self.settings.baidu_ranking_domain, keyword=text)

    def sync(self, *, force: bool = False) -> dict[str, Any]:
        self.seed_default_keywords()
        today = datetime.now(ZoneInfo(self.settings.baidu_ranking_timezone)).date()
        keywords = [row for row in self.repository.list_baidu_keywords(domain=self.settings.baidu_ranking_domain, include_inactive=False)]
        synced = 0
        for item in keywords:
            if not force:
                existing = self.repository._one("SELECT snapshot_id FROM baidu_ranking_snapshots WHERE keyword_id=%s AND observed_date=%s", (item["keyword_id"], today))
                if existing:
                    continue
            result = self.client.query(domain=self.settings.baidu_ranking_domain, keyword=item["keyword"])
            payload = {"snapshot_id": f"baidu-snapshot-{secrets.token_hex(12)}", "keyword_id": item["keyword_id"], "domain": self.settings.baidu_ranking_domain, "keyword": item["keyword"], "observed_date": today, "observed_at_ms": now_ms(), "status": result["status"], "results_json": result.get("results", []), "top_rank": result.get("top_rank"), "matched_url": result.get("matched_url"), "matched_title": result.get("matched_title"), "duration_ms": result.get("duration_ms"), "safe_error_code": result.get("safe_error_code"), "created_at_ms": now_ms()}
            self.repository.upsert_baidu_snapshot(payload)
            synced += 1
        return {"domain": self.settings.baidu_ranking_domain, "observedDate": today.isoformat(), "synced": synced, "total": len(keywords)}


def main() -> None:
    settings = get_settings()
    result = BaiduRankingService(settings, AdminRepository(settings)).sync()
    print(json.dumps(result, ensure_ascii=False))
