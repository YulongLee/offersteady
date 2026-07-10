from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from app.ports.realtime_speech import (
    DesktopDeviceRecord,
    QuestionCandidateRecord,
    RealtimeFrameReceiptRecord,
    RealtimeEvent,
    RealtimePublisherRecord,
    RealtimeSpeechRepository,
    SessionDesktopBindingRecord,
    TranscriptSegmentRecord,
    WebSessionHeartbeatRecord,
)


class InMemoryRealtimeSpeechRepository(RealtimeSpeechRepository):
    def __init__(self, state_file: str | Path | None = None) -> None:
        self.publishers_by_id: dict[str, RealtimePublisherRecord] = {}
        self.publishers_by_token: dict[str, str] = {}
        self.frame_receipts: dict[str, dict[tuple[str, str], RealtimeFrameReceiptRecord]] = {}
        self.transcripts: dict[str, dict[str, TranscriptSegmentRecord]] = {}
        self.candidates: dict[str, QuestionCandidateRecord] = {}
        self.events: dict[str, list[RealtimeEvent]] = {}
        self.session_activity_versions: dict[str, int] = {}
        self.desktop_devices_by_id: dict[str, DesktopDeviceRecord] = {}
        self.desktop_devices_by_code: dict[str, str] = {}
        self.session_bindings: dict[tuple[str, str], SessionDesktopBindingRecord] = {}
        self.web_session_heartbeats: dict[tuple[str, str], WebSessionHeartbeatRecord] = {}
        self.state_file = Path(state_file).expanduser() if state_file else None
        self._load_state()

    def save_desktop_device(self, device: DesktopDeviceRecord) -> DesktopDeviceRecord:
        stored = replace(device)
        self.desktop_devices_by_id[stored.device_id] = stored
        self.desktop_devices_by_code[stored.manual_code] = stored.device_id
        self._persist_state()
        return replace(stored)

    def get_desktop_device_by_code(self, manual_code: str) -> DesktopDeviceRecord | None:
        device_id = self.desktop_devices_by_code.get(manual_code)
        record = self.desktop_devices_by_id.get(device_id or "")
        return replace(record) if record else None

    def save_session_desktop_binding(self, binding: SessionDesktopBindingRecord) -> SessionDesktopBindingRecord:
        stored = replace(binding)
        self.session_bindings[(stored.owner_user_id, stored.session_id)] = stored
        self._bump_session_activity(stored.session_id)
        self._persist_state()
        return replace(stored)

    def save_web_session_heartbeat(self, heartbeat: WebSessionHeartbeatRecord) -> WebSessionHeartbeatRecord:
        stored = replace(heartbeat)
        self.web_session_heartbeats[(stored.owner_user_id, stored.session_id)] = stored
        return replace(stored)

    def get_web_session_heartbeat(self, *, user_id: str, session_id: str) -> WebSessionHeartbeatRecord | None:
        record = self.web_session_heartbeats.get((user_id, session_id))
        return replace(record) if record else None

    def get_session_desktop_binding(self, *, user_id: str, session_id: str) -> SessionDesktopBindingRecord | None:
        record = self.session_bindings.get((user_id, session_id))
        return replace(record) if record else None

    def get_latest_session_desktop_binding_for_device(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord | None:
        items = [
            item for item in self.session_bindings.values()
            if item.device_id == device_id and item.manual_code == manual_code
        ]
        if not items:
            return None
        return replace(sorted(items, key=lambda item: (item.bound_at_ms, item.session_id))[-1])

    def get_latest_session_desktop_binding_by_code(self, *, manual_code: str) -> SessionDesktopBindingRecord | None:
        items = [
            item for item in self.session_bindings.values()
            if item.manual_code == manual_code
        ]
        if not items:
            return None
        return replace(sorted(items, key=lambda item: (item.bound_at_ms, item.session_id))[-1])

    def save_publisher(self, publisher: RealtimePublisherRecord) -> RealtimePublisherRecord:
        stored = replace(publisher)
        self.publishers_by_id[stored.publisher_id] = stored
        self.publishers_by_token[stored.token] = stored.publisher_id
        return replace(stored)

    def get_publisher_by_token(self, token: str) -> RealtimePublisherRecord | None:
        publisher_id = self.publishers_by_token.get(token)
        if publisher_id is None:
            return None
        return self.get_publisher(publisher_id)

    def get_publisher(self, publisher_id: str) -> RealtimePublisherRecord | None:
        record = self.publishers_by_id.get(publisher_id)
        return replace(record) if record else None

    def list_publishers_for_session(self, *, session_id: str) -> list[RealtimePublisherRecord]:
        items = [item for item in self.publishers_by_id.values() if item.session_id == session_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.issued_at_ms)]

    def save_frame_receipt(self, receipt: RealtimeFrameReceiptRecord) -> RealtimeFrameReceiptRecord:
        stored = replace(receipt)
        self.frame_receipts.setdefault(stored.session_id, {})[(stored.source_kind, stored.source_id)] = stored
        return replace(stored)

    def list_frame_receipts_for_session(self, *, session_id: str) -> list[RealtimeFrameReceiptRecord]:
        items = list(self.frame_receipts.get(session_id, {}).values())
        return [replace(item) for item in sorted(items, key=lambda item: (item.source_kind, item.source_id))]

    def save_transcript(self, segment: TranscriptSegmentRecord) -> TranscriptSegmentRecord:
        stored = replace(segment)
        self.transcripts.setdefault(stored.session_id, {})[stored.segment_id] = stored
        self._bump_session_activity(stored.session_id)
        return replace(stored)

    def get_transcript(self, session_id: str, segment_id: str) -> TranscriptSegmentRecord | None:
        record = self.transcripts.get(session_id, {}).get(segment_id)
        return replace(record) if record else None

    def list_transcripts_for_session(self, *, session_id: str) -> list[TranscriptSegmentRecord]:
        items = list(self.transcripts.get(session_id, {}).values())
        return [replace(item) for item in sorted(items, key=lambda item: (item.started_at_ms, item.segment_id, item.revision))]

    def save_candidate(self, candidate: QuestionCandidateRecord) -> QuestionCandidateRecord:
        stored = replace(candidate)
        self.candidates[stored.candidate_id] = stored
        self._bump_session_activity(stored.session_id)
        return replace(stored)

    def get_candidate(self, candidate_id: str) -> QuestionCandidateRecord | None:
        record = self.candidates.get(candidate_id)
        return replace(record) if record else None

    def list_candidates_for_session(self, *, session_id: str) -> list[QuestionCandidateRecord]:
        items = [item for item in self.candidates.values() if item.session_id == session_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.created_at_ms)]

    def save_event(self, event: RealtimeEvent) -> RealtimeEvent:
        stored = replace(event)
        entries = self.events.setdefault(stored.session_id, [])
        entries.append(stored)
        entries.sort(key=lambda item: (item.created_at_ms, item.event_id))
        self._bump_session_activity(stored.session_id)
        return replace(stored)

    def list_events_for_session(self, *, session_id: str) -> list[RealtimeEvent]:
        return [replace(item) for item in self.events.get(session_id, [])]

    def get_session_activity_version(self, *, session_id: str) -> int:
        return self.session_activity_versions.get(session_id, 0)

    def _bump_session_activity(self, session_id: str) -> int:
        next_version = self.session_activity_versions.get(session_id, 0) + 1
        self.session_activity_versions[session_id] = next_version
        return next_version

    def _load_state(self) -> None:
        if not self.state_file or not self.state_file.exists():
            return
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for raw in payload.get("desktopDevices", []):
            try:
                record = DesktopDeviceRecord(
                    device_id=str(raw["device_id"]),
                    manual_code=str(raw["manual_code"]),
                    display_name=str(raw["display_name"]),
                    capabilities=dict(raw.get("capabilities", {})),
                    registered_at_ms=int(raw["registered_at_ms"]),
                    last_seen_at_ms=int(raw["last_seen_at_ms"]),
                    status=str(raw.get("status", "online")),  # type: ignore[arg-type]
                    generation=int(raw.get("generation", 1)),
                )
            except (KeyError, TypeError, ValueError):
                continue
            self.desktop_devices_by_id[record.device_id] = record
            self.desktop_devices_by_code[record.manual_code] = record.device_id
        for raw in payload.get("sessionBindings", []):
            try:
                binding = SessionDesktopBindingRecord(
                    binding_id=str(raw["binding_id"]),
                    session_id=str(raw["session_id"]),
                    owner_user_id=str(raw["owner_user_id"]),
                    device_id=str(raw["device_id"]),
                    manual_code=str(raw["manual_code"]),
                    display_name=str(raw["display_name"]),
                    capabilities=dict(raw.get("capabilities", {})),
                    bound_at_ms=int(raw["bound_at_ms"]),
                    last_seen_at_ms=int(raw["last_seen_at_ms"]),
                    status=str(raw.get("status", "bound")),  # type: ignore[arg-type]
                    binding_generation=int(raw.get("binding_generation", raw.get("bindingGeneration", 1))),
                )
            except (KeyError, TypeError, ValueError):
                continue
            self.session_bindings[(binding.owner_user_id, binding.session_id)] = binding

    def _persist_state(self) -> None:
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "desktopDevices": [
                {
                    "device_id": item.device_id,
                    "manual_code": item.manual_code,
                    "display_name": item.display_name,
                    "capabilities": item.capabilities,
                    "registered_at_ms": item.registered_at_ms,
                    "last_seen_at_ms": item.last_seen_at_ms,
                    "status": item.status,
                    "generation": item.generation,
                }
                for item in sorted(self.desktop_devices_by_id.values(), key=lambda entry: (entry.last_seen_at_ms, entry.device_id))
            ],
            "sessionBindings": [
                {
                    "binding_id": item.binding_id,
                    "session_id": item.session_id,
                    "owner_user_id": item.owner_user_id,
                    "device_id": item.device_id,
                    "manual_code": item.manual_code,
                    "display_name": item.display_name,
                    "capabilities": item.capabilities,
                    "bound_at_ms": item.bound_at_ms,
                    "last_seen_at_ms": item.last_seen_at_ms,
                    "status": item.status,
                    "binding_generation": item.binding_generation,
                }
                for item in sorted(self.session_bindings.values(), key=lambda entry: (entry.bound_at_ms, entry.session_id))
            ],
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
