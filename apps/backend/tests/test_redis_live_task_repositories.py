from __future__ import annotations

import time
from contextlib import nullcontext
from dataclasses import replace

from app.core.config import Settings
from app.ports.chat import ChatAnswerTaskRecord
from app.ports.screenshot_answer import RemoteScreenshotCaptureRequest, ScreenshotAnswerTaskRecord
from app.services.redis_live_task_repositories import RedisChatRepository, RedisScreenshotAnswerRepository


class _Pipeline:
    def __init__(self, redis) -> None:  # noqa: ANN001
        self.redis = redis
        self.operations = []

    def set(self, *args, **kwargs): self.operations.append(("set", args, kwargs)); return self
    def zadd(self, *args, **kwargs): self.operations.append(("zadd", args, kwargs)); return self
    def expire(self, *args, **kwargs): self.operations.append(("expire", args, kwargs)); return self
    def execute(self):
        for name, args, kwargs in self.operations:
            getattr(self.redis, name)(*args, **kwargs)


class FakeRedis:
    def __init__(self) -> None:
        self.values = {}
        self.sorted_sets = {}

    def ping(self): return True
    def lock(self, *args, **kwargs): return nullcontext()
    def pipeline(self, transaction=True): return _Pipeline(self)
    def set(self, key, value, ex=None): self.values[key] = value
    def get(self, key): return self.values.get(key)
    def expire(self, key, ttl): return True
    def zadd(self, key, mapping): self.sorted_sets.setdefault(key, {}).update(mapping)
    def zrange(self, key, start, end):
        members = [item[0] for item in sorted(self.sorted_sets.get(key, {}).items(), key=lambda item: item[1])]
        return members[start:] if end == -1 else members[start:end + 1]


def _settings() -> Settings:
    return Settings(_env_file=None, redis_url="redis://unused", live_task_stale_seconds=30)


def test_chat_tasks_survive_repository_recreation_and_terminal_state_wins() -> None:
    redis = FakeRedis()
    first = RedisChatRepository(_settings(), redis_client=redis)
    now = int(time.time() * 1000)
    task = ChatAnswerTaskRecord(
        task_id="answer-1", session_id="session-1", owner_user_id="user-1", question="问题",
        answer_text="完整答案", status="completed", stream_mode=True,
        created_at_ms=now, updated_at_ms=now, completed_at_ms=now,
    )
    first.save_task(task)

    restarted = RedisChatRepository(_settings(), redis_client=redis)
    assert restarted.get_task(task.task_id) == task
    stale_write = replace(task, status="streaming", answer_text="部分", updated_at_ms=now + 1, completed_at_ms=None)
    assert restarted.save_task(stale_write).status == "completed"
    assert restarted.list_tasks_for_session(session_id="session-1") == [task]


def test_stale_chat_task_recovers_as_safe_failure() -> None:
    redis = FakeRedis()
    repository = RedisChatRepository(_settings(), redis_client=redis)
    old = int(time.time() * 1000) - 60_000
    repository.save_task(ChatAnswerTaskRecord(
        task_id="answer-stale", session_id="session-1", owner_user_id="user-1", question="问题",
        answer_text="", status="streaming", stream_mode=True, created_at_ms=old, updated_at_ms=old,
    ))
    recovered = repository.get_task("answer-stale")
    assert recovered is not None
    assert recovered.status == "failed"
    assert recovered.error_code == "runtime_task_interrupted"


def test_screenshot_runtime_persists_tasks_requests_and_no_media_bytes() -> None:
    redis = FakeRedis()
    first = RedisScreenshotAnswerRepository(_settings(), redis_client=redis)
    now = int(time.time() * 1000)
    task = ScreenshotAnswerTaskRecord(
        task_id="shot-task", session_id="session-1", owner_user_id="user-1", instruction="截图题",
        answer_text="答案", status="completed", stream_mode=True, created_at_ms=now, updated_at_ms=now,
    )
    request = RemoteScreenshotCaptureRequest(
        request_id="shot-request", session_id="session-1", owner_user_id="user-1",
        device_id="device-1", manual_code="123456", instruction="截图题", status="requested",
        created_at_ms=now, updated_at_ms=now,
    )
    first.save_task(task)
    first.save_remote_capture_request(request)

    restarted = RedisScreenshotAnswerRepository(_settings(), redis_client=redis)
    assert restarted.get_task(task.task_id) == task
    assert restarted.get_next_pending_remote_capture_request(device_id="device-1", manual_code="123456") == request
    serialized = " ".join(str(value) for value in redis.values.values())
    assert "base64" not in serialized
    assert "payload_bytes" not in serialized
