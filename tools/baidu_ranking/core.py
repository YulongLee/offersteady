from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://seozbbdpcpm.api.bdymkt.com/seo/baidu/pc/ranking"
DEFAULT_KEYWORDS = [
    "AI面试助手", "面试助手", "AI面试辅助", "实时面试辅助", "面试AI",
    "AI面试工具", "AI面试实时回答", "程序员面试助手", "AI面试助手哪个好", "AI面试助手价格",
]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_keywords() -> list[str]:
    raw = os.getenv("BAIDU_RANKING_KEYWORDS", "")
    if not raw.strip():
        return list(DEFAULT_KEYWORDS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class RankingConfig:
    endpoint: str = field(default_factory=lambda: os.getenv("BAIDU_RANKING_ENDPOINT", DEFAULT_ENDPOINT))
    domain: str = field(default_factory=lambda: os.getenv("BAIDU_RANKING_DOMAIN", "mianshiwen.cn"))
    access_key: str | None = field(default_factory=lambda: os.getenv("BAIDU_RANKING_ACCESS_KEY") or None)
    secret_key: str | None = field(default_factory=lambda: os.getenv("BAIDU_RANKING_SECRET_KEY") or None)
    app_code: str | None = field(default_factory=lambda: os.getenv("BAIDU_RANKING_APP_CODE") or None)
    keywords: list[str] = field(default_factory=_env_keywords)
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("BAIDU_RANKING_TIMEOUT_SECONDS", "20")))
    retry_attempts: int = field(default_factory=lambda: max(0, int(os.getenv("BAIDU_RANKING_RETRY_ATTEMPTS", "1"))))
    delay_seconds: float = field(default_factory=lambda: max(0.2, float(os.getenv("BAIDU_RANKING_DELAY_SECONDS", "0.5"))))
    max_keywords: int = field(default_factory=lambda: max(1, int(os.getenv("BAIDU_RANKING_MAX_KEYWORDS", "50"))))

    def validate(self) -> str | None:
        if not self.endpoint.strip():
            return "missing_endpoint"
        if not self.domain.strip():
            return "missing_domain"
        if bool(self.access_key) != bool(self.secret_key):
            return "incomplete_access_key_credentials"
        if not (self.app_code or (self.access_key and self.secret_key)):
            return "missing_credentials"
        if self.timeout_seconds <= 0 or self.retry_attempts > 3:
            return "invalid_request_limits"
        return None


@dataclass(frozen=True)
class RankingEntry:
    rank_label: str
    title: str
    url: str


@dataclass(frozen=True)
class RankingResult:
    domain: str
    keyword: str
    observed_at: str
    status: str
    rank_label: str | None = None
    title: str | None = None
    url: str | None = None
    results: list[RankingEntry] = field(default_factory=list)
    safe_error_code: str | None = None
    provider_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [asdict(item) for item in self.results]
        return payload


def _signature(method: str, url: str, access_key: str, secret_key: str) -> str:
    parts = urlsplit(url)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expiration = "1800"
    signed_headers = "host;content-type"
    canonical_headers = f"content-type:{quote('application/x-www-form-urlencoded', safe='-_.~')}\nhost:{quote(parts.netloc, safe='-_.~')}"
    canonical_request = "\n".join([method.upper(), quote(parts.path or "/", safe="/-_.~"), "", canonical_headers])
    signing_key = hmac.new(secret_key.encode(), f"bce-auth-v1/{access_key}/{timestamp}/{expiration}".encode(), hashlib.sha256).hexdigest()
    digest = hmac.new(signing_key.encode(), canonical_request.encode(), hashlib.sha256).hexdigest()
    return f"bce-auth-v1/{access_key}/{timestamp}/{expiration}/{signed_headers}/{digest}"


def _safe_provider_error(code: int | None, message: str) -> str:
    if code in {401, 403} or "签名" in message or "认证" in message or "鉴权" in message:
        return "authentication_failed"
    if code == 429 or "额度" in message or "次数" in message:
        return "quota_exceeded"
    if code is not None and code >= 500:
        return "provider_error"
    return "invalid_response"


class BaiduRankingClient:
    """Small urllib-based adapter so the local tool has no new dependency."""

    def __init__(self, config: RankingConfig, opener: Callable[..., Any] = urlopen) -> None:
        self.config = config
        self._opener = opener

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.config.access_key and self.config.secret_key:
            headers["X-Bce-Signature"] = _signature("POST", self.config.endpoint, self.config.access_key, self.config.secret_key)
        elif self.config.app_code:
            headers["X-Bce-Signature"] = f"AppCode/{self.config.app_code}"
        return headers

    def query(self, keyword: str) -> RankingResult:
        observed_at = datetime.now(timezone.utc).isoformat()
        if (error := self.config.validate()) is not None:
            return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code=error)
        if not keyword.strip():
            return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="missing_keyword")
        body = urlencode({"domain": self.config.domain, "keyword": keyword}).encode()
        request = Request(self.config.endpoint, data=body, headers=self._headers(), method="POST")
        attempts = self.config.retry_attempts + 1
        for attempt in range(attempts):
            try:
                with self._opener(request, timeout=self.config.timeout_seconds) as response:
                    status_code = getattr(response, "status", 200)
                    raw = response.read().decode("utf-8", errors="replace")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="invalid_response", provider_code=status_code)
                provider_code = payload.get("code") if isinstance(payload.get("code"), int) else status_code
                if provider_code != 200 or payload.get("success") is False:
                    message = str(payload.get("msg") or payload.get("message") or "")
                    return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code=_safe_provider_error(provider_code, message), provider_code=provider_code)
                data = payload.get("data")
                raw_ranks = data.get("Ranks", []) if isinstance(data, dict) else []
                if not isinstance(raw_ranks, list):
                    return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="invalid_response", provider_code=provider_code)
                entries: list[RankingEntry] = []
                for index, item in enumerate(raw_ranks[:50], start=1):
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("RankStr") or item.get("rank") or index)
                    entries.append(RankingEntry(label, str(item.get("Title") or item.get("title") or ""), str(item.get("Url") or item.get("url") or "")))
                first = entries[0] if entries else None
                return RankingResult(self.config.domain, keyword, observed_at, "ranked" if entries else "not_found", first.rank_label if first else None, first.title if first else None, first.url if first else None, entries, provider_code=provider_code)
            except TimeoutError:
                if attempt + 1 == attempts:
                    return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="timeout")
            except HTTPError as exc:
                message = exc.read().decode("utf-8", errors="replace")[:1000]
                if exc.code >= 500 and attempt + 1 < attempts:
                    continue
                return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code=_safe_provider_error(exc.code, message), provider_code=exc.code)
            except (URLError, OSError):
                if attempt + 1 == attempts:
                    return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="network_error")
            except (json.JSONDecodeError, UnicodeError):
                return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="invalid_response")
        return RankingResult(self.config.domain, keyword, observed_at, "error", safe_error_code="provider_error")


def run_queries(config: RankingConfig, keywords: Iterable[str], *, batch: bool = False) -> list[RankingResult]:
    selected = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
    if len(selected) > config.max_keywords:
        raise ValueError("keyword_limit_exceeded")
    if len(selected) > 1 and not batch:
        raise ValueError("batch_confirmation_required")
    client = BaiduRankingClient(config)
    results: list[RankingResult] = []
    for index, keyword in enumerate(selected):
        if index:
            time.sleep(config.delay_seconds)
        results.append(client.query(keyword))
    return results


def write_reports(results: list[RankingResult], output_dir: str | Path, *, formats: set[str]) -> list[Path]:
    destination = Path(output_dir).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "results": [item.to_dict() for item in results]}
    paths: list[Path] = []
    if "json" in formats:
        path = destination / f"baidu-ranking-{stamp}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    if "markdown" in formats:
        lines = ["# Baidu PC ranking report", "", f"Generated: {payload['generated_at']}", ""]
        for result in results:
            lines.extend([f"## {result.keyword}", "", f"- Domain: `{result.domain}`", f"- Observed: `{result.observed_at}`", f"- Status: **{result.status}**"])
            if result.rank_label:
                lines.append(f"- Rank label: `{result.rank_label}` (provider format; not converted to an absolute rank)")
            if result.safe_error_code:
                lines.append(f"- Error: `{result.safe_error_code}`")
            if result.url:
                lines.append(f"- Matched URL: {result.url}")
            if result.title:
                lines.append(f"- Matched title: {result.title}")
            if result.results:
                lines.extend(["", "| Provider rank | Title | URL |", "| --- | --- | --- |"])
                for entry in result.results[:50]:
                    title = entry.title.replace("|", "\\|")
                    lines.append(f"| {entry.rank_label} | {title} | {entry.url} |")
            lines.append("")
        path = destination / f"baidu-ranking-{stamp}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)
    return paths
