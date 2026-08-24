from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from statistics import median
from time import perf_counter, process_time

from fastapi.testclient import TestClient

from app.main import create_app


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def unwrap(response):
    response.raise_for_status()
    return response.json()["data"]


def request_timed(client: TestClient, path: str, params: dict[str, object]) -> float:
    started = perf_counter()
    response = client.get(path, params=params)
    response.raise_for_status()
    return (perf_counter() - started) * 1_000


def run_scenario(concurrency: int) -> dict[str, object]:
    client = TestClient(create_app())
    sessions: list[tuple[str, str, str, int]] = []
    for index in range(concurrency):
        user_id = f"synthetic-recovery-user-{concurrency}-{index}"
        session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "合成恢复负载"}))
        session_id = session["sessionId"]
        unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
        lease = unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
            "userId": user_id,
            "bindingId": None,
            "page": "live",
            "pageInstanceId": f"synthetic-page-{index}",
        }))
        sessions.append((user_id, session_id, lease["pageInstanceId"], lease["leaseGeneration"]))

    legacy_calls = [
        (f"/api/v1/realtime-speech/sessions/{session_id}/{suffix}", {"userId": user_id})
        for user_id, session_id, _page_id, _generation in sessions
        for suffix in ("transcripts", "question-candidates", "events", "runtime")
    ]
    snapshot_calls = [
        (
            f"/api/v1/realtime-speech/sessions/{session_id}/snapshot",
            {"userId": user_id, "pageInstanceId": page_id, "leaseGeneration": generation},
        )
        for user_id, session_id, page_id, generation in sessions
    ]

    def measure(calls: list[tuple[str, dict[str, object]]]) -> dict[str, object]:
        wall_started = perf_counter()
        cpu_started = process_time()
        with ThreadPoolExecutor(max_workers=max(1, min(16, len(calls)))) as executor:
            durations = list(executor.map(lambda item: request_timed(client, item[0], item[1]), calls))
        return {
            "requests": len(calls),
            "wallMs": round((perf_counter() - wall_started) * 1_000, 2),
            "cpuMs": round((process_time() - cpu_started) * 1_000, 2),
            "p50Ms": round(median(durations), 2),
            "p95Ms": round(percentile(durations, 0.95), 2),
            "p99Ms": round(percentile(durations, 0.99), 2),
            "errors": 0,
        }

    legacy = measure(legacy_calls)
    snapshot = measure(snapshot_calls)
    return {
        "concurrency": concurrency,
        "legacyFourEndpointRecovery": legacy,
        "aggregatedSnapshotRecovery": snapshot,
        "requestReductionPercent": round((1 - snapshot["requests"] / legacy["requests"]) * 100, 1),
    }


if __name__ == "__main__":
    print(json.dumps({
        "fixture": "synthetic-content-free",
        "scenarios": [run_scenario(value) for value in (1, 5, 10)],
        "disconnectPolicyMs": [0, 2_000, 4_000, 8_000, 15_000],
    }, ensure_ascii=False, indent=2))
