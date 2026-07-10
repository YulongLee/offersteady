from __future__ import annotations

from dataclasses import replace

from app.ports.document_processing import ProcessingTaskEvent, ProcessingTaskRecord, ProcessingTaskRepository


class InMemoryProcessingTaskRepository(ProcessingTaskRepository):
    def __init__(self) -> None:
        self.tasks: dict[str, ProcessingTaskRecord] = {}
        self.events: dict[str, list[ProcessingTaskEvent]] = {}

    def save_task(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord:
        stored = replace(task)
        self.tasks[stored.task_id] = stored
        return replace(stored)

    def get_task(self, task_id: str) -> ProcessingTaskRecord | None:
        record = self.tasks.get(task_id)
        return replace(record) if record else None

    def list_tasks_for_user(self, *, user_id: str | None = None, document_id: str | None = None) -> list[ProcessingTaskRecord]:
        records = list(self.tasks.values())
        if user_id is not None:
            records = [record for record in records if record.owner_user_id == user_id]
        if document_id is not None:
            records = [record for record in records if record.document_id == document_id]
        return [replace(record) for record in sorted(records, key=lambda item: item.updated_at_ms, reverse=True)]

    def save_event(self, event: ProcessingTaskEvent) -> ProcessingTaskEvent:
        stored = replace(event)
        self.events.setdefault(stored.task_id, []).append(stored)
        return replace(stored)

    def list_events_for_task(self, task_id: str) -> list[ProcessingTaskEvent]:
        return [replace(event) for event in self.events.get(task_id, [])]

