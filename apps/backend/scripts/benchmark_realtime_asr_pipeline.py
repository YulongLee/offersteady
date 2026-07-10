from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from statistics import mean
from time import perf_counter, time

from fastapi.testclient import TestClient

from app.main import create_app


def unwrap(response):
    payload = response.json()
    if response.status_code >= 400:
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    return payload["data"]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def run_benchmark() -> dict[str, object]:
    client = TestClient(create_app())
    session = unwrap(client.post("/api/v1/sessions", json={
        "userId": "benchmark-user",
        "title": "Realtime ASR Benchmark",
    }))
    session_id = session["sessionId"]
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "benchmark-user"}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "benchmark-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "benchmark-microphone",
    }))

    roundtrip_ms: list[float] = []
    samples = [
        ("bench-1", 1, "我正在做自我介绍"),
        ("bench-2", 2, "最近负责一个前端性能治理项目"),
        ("bench-3", 3, "我主要优化了首屏性能和监控链路"),
        ("bench-4", 4, "也做过工程化和稳定性建设"),
        ("bench-5", 5, "可以继续聊聊最有挑战的项目"),
    ]
    runtime_snapshots: list[dict[str, object]] = []

    with client.websocket_connect(f"/api/v1/realtime-speech/ws?token={publisher['token']}") as websocket:
        for segment_id, sequence, text in samples:
            payload = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            started = perf_counter()
            websocket.send_json({
                "type": "audio-frame",
                "deviceId": "benchmark-device",
                "sourceId": "mic-default",
                "sequence": sequence,
                "sourceKind": "microphone",
                "segmentId": segment_id,
                "revision": 1,
                "capturedAtMs": int(time() * 1000),
                "startedAtMs": int(time() * 1000),
                "endedAtMs": int(time() * 1000) + 600,
                "durationMs": 600,
                "codec": "pcm-s16le",
                "sampleRateHz": 16000,
                "channels": 1,
                "isFinal": True,
                "audioBase64": payload,
            })
            event = websocket.receive_json()
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            if event["kind"] != "transcript-updated":
                raise RuntimeError(f"unexpected event order: {event}")
            roundtrip_ms.append(elapsed_ms)
            runtime_snapshots.append(unwrap(client.get(
                f"/api/v1/realtime-speech/sessions/{session_id}/runtime",
                params={"userId": "benchmark-user"},
            )))

    latest_runtime = runtime_snapshots[-1]
    microphone_perf = (latest_runtime.get("performance") or {}).get("latestBySource", {}).get("microphone", {})
    microphone_counters = (latest_runtime.get("performance") or {}).get("countersBySource", {}).get("microphone", {})
    result = {
        "generatedAt": int(time() * 1000),
        "sessionId": session_id,
        "sampleCount": len(roundtrip_ms),
        "transportRoundtripMs": {
            "avg": round(mean(roundtrip_ms), 2),
            "p50": round(percentile(roundtrip_ms, 0.5), 2),
            "p95": round(percentile(roundtrip_ms, 0.95), 2),
            "max": round(max(roundtrip_ms), 2),
        },
        "latestMicrophoneTiming": microphone_perf,
        "latestMicrophoneCounters": microphone_counters,
    }
    return result


def main() -> None:
    os.environ.setdefault("PYTEST_CURRENT_TEST", "benchmark_realtime_asr_pipeline")
    result = run_benchmark()
    target = Path("artifacts/realtime-asr-benchmarks")
    target.mkdir(parents=True, exist_ok=True)
    output = target / "baseline.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
