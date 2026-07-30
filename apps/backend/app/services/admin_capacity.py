from __future__ import annotations

import json
import os
from collections import deque
from pathlib import Path
from threading import Lock
from time import monotonic, time
from typing import Any

import redis

from app.core.config import Settings


CAPACITY_KEY = "offersteady:admin:capacity:v1"
REQUEST_WINDOW_MS = 5 * 60 * 1000
DISPLAY_WINDOW_MS = 60 * 60 * 1000


def _now_ms() -> int:
    return int(time() * 1000)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * fraction + 0.999999)) - 1))
    return ordered[index]


def capacity_level(value: float | int | None, warning: float | int | None, critical: float | int | None) -> str:
    if value is None:
        return "unavailable"
    if critical is not None and value >= critical:
        return "critical"
    if warning is not None and value >= warning:
        return "warning"
    return "healthy"


class RequestWindow:
    def __init__(self) -> None:
        self._events: deque[tuple[int, float, int]] = deque(maxlen=20_000)
        self._lock = Lock()

    def record(self, *, path: str, elapsed_ms: float, status_code: int) -> None:
        if path in {"/healthz", "/api/v1/admin/capacity"}:
            return
        current = _now_ms()
        with self._lock:
            self._events.append((current, elapsed_ms, status_code))
            self._prune(current)

    def summary(self, current: int | None = None) -> dict[str, float]:
        now = current or _now_ms()
        with self._lock:
            self._prune(now)
            events = list(self._events)
        durations = [item[1] for item in events]
        errors = sum(1 for item in events if item[2] >= 500)
        span_minutes = max(1.0, min(5.0, (now - events[0][0]) / 60_000)) if events else 1.0
        return {
            "apiP95Ms": round(percentile(durations, 0.95) or 0.0, 2),
            "apiErrorRate": round(errors * 100 / len(events), 2) if events else 0.0,
            "requestsPerMinute": round(len(events) / span_minutes, 2),
        }

    def _prune(self, current: int) -> None:
        while self._events and self._events[0][0] < current - REQUEST_WINDOW_MS:
            self._events.popleft()


class AdminCapacityMonitor:
    def __init__(self, settings: Settings, repository: Any) -> None:
        self.settings = settings
        self.repository = repository
        self.requests = RequestWindow()
        self._samples: deque[dict[str, Any]] = deque(maxlen=720)
        self._lock = Lock()
        self._cpu_lock = Lock()
        self._previous_cpu: tuple[int, float] | None = None
        self._redis = (
            redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=settings.redis_socket_timeout_seconds,
                socket_connect_timeout=settings.redis_socket_timeout_seconds,
            )
            if settings.redis_url else None
        )

    def record_request(self, *, path: str, elapsed_ms: float, status_code: int) -> None:
        self.requests.record(path=path, elapsed_ms=elapsed_ms, status_code=status_code)

    def sample(self) -> dict[str, Any]:
        current = _now_ms()
        database = self._safe_database_counts()
        runtime = self._safe_runtime_counts(current)
        resources = self._resource_counts()
        sample = {
            "atMs": current,
            **database,
            **runtime,
            **resources,
            **self.requests.summary(current),
        }
        with self._lock:
            self._samples.append(sample)
        self._persist(sample)
        return sample

    def report(self) -> dict[str, Any]:
        samples = self._load_samples()
        if not samples:
            samples = [self.sample()]
        current = samples[-1]
        database_limit = current.get("databaseConnectionLimit")
        definitions = [
            ("activeInterviews", "进行中面试", "场", self.settings.admin_capacity_active_interviews_warning, self.settings.admin_capacity_active_interviews_critical, "最近 20 分钟仍有活动的 live 面试。"),
            ("activeWebSessions", "在线面试页面", "页", None, None, "仍在发送有效心跳的实时面试页面。"),
            ("onlineDevices", "在线桌面助手", "台", None, None, "最近 45 秒仍有心跳的桌面助手。"),
            ("activeAudioStreams", "活跃 ASR 音频流", "路", self.settings.admin_capacity_audio_streams_warning, self.settings.admin_capacity_audio_streams_critical, "最近 30 秒收到真实音频帧的去重音轨。"),
            ("cpuPercent", "后端容器 CPU", "%", self.settings.admin_capacity_cpu_warning_percent, self.settings.admin_capacity_cpu_critical_percent, "相对容器 CPU 配额的使用率。"),
            ("memoryPercent", "后端容器内存", "%", self.settings.admin_capacity_memory_warning_percent, self.settings.admin_capacity_memory_critical_percent, "相对容器内存上限的使用率。"),
            ("apiP95Ms", "API P95", "ms", self.settings.admin_capacity_api_p95_warning_ms, self.settings.admin_capacity_api_p95_critical_ms, "最近 5 分钟后端请求耗时 P95。"),
            ("apiErrorRate", "API 5xx 错误率", "%", self.settings.admin_capacity_error_rate_warning_percent, self.settings.admin_capacity_error_rate_critical_percent, "最近 5 分钟服务端错误占比。"),
            ("databaseConnections", "数据库连接", "条", database_limit * 0.7 if database_limit else None, database_limit * 0.9 if database_limit else None, "当前数据库连接数及其最大连接配额。"),
        ]
        metrics = []
        for key, label, unit, warning, critical, description in definitions:
            value = current.get(key)
            metrics.append({
                "key": key,
                "label": label,
                "unit": unit,
                "value": value,
                "warning": warning,
                "critical": critical,
                "level": capacity_level(value, warning, critical),
                "description": description,
                "points": [{"atMs": item["atMs"], "value": item.get(key)} for item in samples],
            })
        return {
            "generatedAtMs": _now_ms(),
            "sampleIntervalSeconds": self.settings.admin_capacity_sample_interval_seconds,
            "windowMinutes": 60,
            "metrics": metrics,
            "supporting": {
                "activeUsers": current.get("activeUsers"),
                "requestsPerMinute": current.get("requestsPerMinute"),
                "databaseConnectionLimit": database_limit,
            },
        }

    def _safe_database_counts(self) -> dict[str, int | None]:
        try:
            return self.repository.capacity_counts()
        except Exception:
            return {
                "activeInterviews": None,
                "activeUsers": None,
                "databaseConnections": None,
                "databaseConnectionLimit": None,
            }

    def _safe_runtime_counts(self, current: int) -> dict[str, int | None]:
        if self._redis is None:
            return {"activeWebSessions": None, "onlineDevices": None, "activeAudioStreams": None}
        try:
            raw = self._redis.get("offersteady:realtime:runtime:v2")
            payload = json.loads(raw) if raw else {}
            devices = payload.get("devices", [])
            heartbeats = payload.get("heartbeats", [])
            receipts = [json.loads(item) for item in self._redis.hvals("offersteady:realtime:runtime:v2:receipts")]
            online_devices = {
                str(item.get("device_id"))
                for item in devices
                if item.get("status") == "online"
                and int(item.get("last_seen_at_ms") or 0) >= current - self.settings.realtime_desktop_heartbeat_ttl_seconds * 1000
            }
            active_web = {
                str(item.get("session_id"))
                for item in heartbeats
                if item.get("page") == "live"
                and int(item.get("lease_expires_at_ms") or 0) >= current
            }
            active_audio = {
                (str(item.get("session_id")), str(item.get("source_kind")), str(item.get("source_id")))
                for item in receipts
                if item.get("source_id") != "diagnostic-pcm-probe"
                and int(item.get("frame_count") or 0) > 0
                and int(item.get("received_at_ms") or 0) >= current - 30_000
                and item.get("asr_status") in {"pending", "accepted"}
            }
            return {
                "activeWebSessions": len(active_web),
                "onlineDevices": len(online_devices),
                "activeAudioStreams": len(active_audio),
            }
        except Exception:
            return {"activeWebSessions": None, "onlineDevices": None, "activeAudioStreams": None}

    def _resource_counts(self) -> dict[str, float | None]:
        return {
            "cpuPercent": self._cpu_percent(),
            "memoryPercent": self._memory_percent(),
        }

    def _cpu_percent(self) -> float | None:
        try:
            values = {}
            for line in Path("/sys/fs/cgroup/cpu.stat").read_text(encoding="ascii").splitlines():
                key, value = line.split()
                values[key] = int(value)
            quota_text = Path("/sys/fs/cgroup/cpu.max").read_text(encoding="ascii").strip().split()
            quota = float(quota_text[0]) if quota_text[0] != "max" else float(os.cpu_count() or 1) * float(quota_text[1])
            period = float(quota_text[1])
            cores = max(0.01, quota / period)
            usage = int(values["usage_usec"])
            observed = monotonic()
            with self._cpu_lock:
                previous = self._previous_cpu
                self._previous_cpu = (usage, observed)
            if previous is None or observed <= previous[1]:
                return None
            percent = (usage - previous[0]) / ((observed - previous[1]) * 1_000_000 * cores) * 100
            return round(max(0.0, percent), 2)
        except (OSError, KeyError, ValueError):
            return None

    @staticmethod
    def _memory_percent() -> float | None:
        try:
            current = int(Path("/sys/fs/cgroup/memory.current").read_text(encoding="ascii").strip())
            maximum_text = Path("/sys/fs/cgroup/memory.max").read_text(encoding="ascii").strip()
            if maximum_text == "max":
                return None
            maximum = int(maximum_text)
            return round(current * 100 / maximum, 2) if maximum > 0 else None
        except (OSError, ValueError):
            return None

    def _persist(self, sample: dict[str, Any]) -> None:
        if self._redis is None:
            return
        try:
            encoded = json.dumps(sample, ensure_ascii=True, separators=(",", ":"))
            pipeline = self._redis.pipeline()
            pipeline.zadd(CAPACITY_KEY, {encoded: int(sample["atMs"])})
            pipeline.zremrangebyscore(CAPACITY_KEY, 0, int(sample["atMs"]) - self.settings.admin_capacity_retention_seconds * 1000)
            pipeline.expire(CAPACITY_KEY, self.settings.admin_capacity_retention_seconds)
            pipeline.execute()
        except Exception:
            return

    def _load_samples(self) -> list[dict[str, Any]]:
        cutoff = _now_ms() - DISPLAY_WINDOW_MS
        if self._redis is not None:
            try:
                return [json.loads(item) for item in self._redis.zrangebyscore(CAPACITY_KEY, cutoff, "+inf")]
            except Exception:
                pass
        with self._lock:
            return [item for item in self._samples if int(item["atMs"]) >= cutoff]
