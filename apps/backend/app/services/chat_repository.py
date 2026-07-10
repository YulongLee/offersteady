from __future__ import annotations

from dataclasses import replace

from app.ports.chat import ChatAnswerTaskRecord, ChatRepository


class InMemoryChatRepository(ChatRepository):
    def __init__(self) -> None:
        self.tasks: dict[str, ChatAnswerTaskRecord] = {}

    def save_task(self, task: ChatAnswerTaskRecord) -> ChatAnswerTaskRecord:
        stored = replace(task)
        self.tasks[stored.task_id] = stored
        return replace(stored)

    def get_task(self, task_id: str) -> ChatAnswerTaskRecord | None:
        record = self.tasks.get(task_id)
        return replace(record) if record else None

    def list_tasks_for_session(self, *, session_id: str) -> list[ChatAnswerTaskRecord]:
        items = [task for task in self.tasks.values() if task.session_id == session_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.created_at_ms)]
