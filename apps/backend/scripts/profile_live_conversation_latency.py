from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "realtime-asr-benchmarks"


def _unwrap(response):
    payload = response.json()
    if response.status_code >= 400:
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    return payload["data"]


def _synthesize_pcm16le_16khz(text: str) -> bytes:
    with TemporaryDirectory() as directory:
        aiff_path = Path(directory) / "sample.aiff"
        wav_path = Path(directory) / "sample.wav"
        subprocess.run(
            ["/usr/bin/say", "-o", str(aiff_path), text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff_path), str(wav_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with wave.open(str(wav_path), "rb") as wav_file:
            return wav_file.readframes(wav_file.getnframes())


def _clear_backend_caches() -> None:
    from app.core.config import get_settings
    from app import deps

    get_settings.cache_clear()
    deps.realtime_speech_repository.cache_clear()
    deps.realtime_asr_gateway.cache_clear()
    deps.realtime_speech_service.cache_clear()
    deps.session_service.cache_clear()
    deps.chat_service.cache_clear()


def _create_client(*, synthetic: bool) -> TestClient:
    if synthetic:
        os.environ["PYTEST_CURRENT_TEST"] = "profile_live_conversation_latency"
        os.environ.pop("OFFERSTEADY_TEST_USE_REMOTE_REALTIME_ASR", None)
    else:
        os.environ.pop("PYTEST_CURRENT_TEST", None)
    _clear_backend_caches()
    from app.main import create_app

    return TestClient(create_app())


def run_synthetic_internal_probe() -> dict[str, object]:
    client = _create_client(synthetic=True)
    session = _unwrap(client.post("/api/v1/sessions", json={
        "userId": "latency-synthetic-user",
        "title": "Synthetic Latency Probe",
    }))
    session_id = session["sessionId"]
    _unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": "latency-synthetic-user"}))
    publisher = _unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": "latency-synthetic-user",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": "synthetic-probe",
    }))

    captured_at_ms = int(time.time() * 1000)
    started = time.perf_counter()
    payload = base64.b64encode("我正在做内部链路延迟测试".encode("utf-8")).decode("utf-8")
    _unwrap(client.post("/api/v1/realtime-speech/frames", json={
        "type": "audio-frame",
        "token": publisher["token"],
        "deviceId": "synthetic-device",
        "sourceId": "mic-default",
        "sequence": 1,
        "sourceKind": "microphone",
        "segmentId": "seg-synthetic-1",
        "revision": 1,
        "capturedAtMs": captured_at_ms,
        "sentAtMs": captured_at_ms + 1,
        "startedAtMs": captured_at_ms,
        "endedAtMs": captured_at_ms + 800,
        "durationMs": 800,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": True,
        "traceId": "trace-synthetic-1",
        "audioBase64": payload,
    }))
    ack_ms = round((time.perf_counter() - started) * 1000, 2)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        transcripts = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": "latency-synthetic-user"}))
        if transcripts["transcripts"]:
            runtime = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": "latency-synthetic-user"}))
            latest = transcripts["transcripts"][-1]
            return {
                "mode": "synthetic-internal",
                "postAckMs": ack_ms,
                "timing": latest["performance"],
                "runtimeStage": runtime["stage"],
                "dominantBottleneck": runtime.get("dominantBottleneck"),
                "anomalyReasons": runtime.get("anomalyReasons"),
                "text": latest["text"],
            }
        time.sleep(0.02)
    raise RuntimeError("synthetic probe timed out")


def run_remote_paced_probe(*, turn_detection_mode: str, text: str) -> dict[str, object]:
    os.environ["OFFERSTEADY_REALTIME_ASR_TURN_DETECTION_MODE"] = turn_detection_mode
    client = _create_client(synthetic=False)
    pcm = _synthesize_pcm16le_16khz(text)
    session = _unwrap(client.post("/api/v1/sessions", json={
        "userId": f"latency-remote-{turn_detection_mode}",
        "title": f"Remote Latency Probe ({turn_detection_mode})",
    }))
    session_id = session["sessionId"]
    _unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": f"probe-device-{turn_detection_mode}",
        "manualCode": "445566" if turn_detection_mode == "manual" else "445567",
        "displayName": f"Probe Device {turn_detection_mode}",
        "capabilities": {"microphone": "granted", "systemAudio": "granted", "screenCapture": False},
    }))
    binding = _unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={
        "userId": f"latency-remote-{turn_detection_mode}",
        "manualCode": "445566" if turn_detection_mode == "manual" else "445567",
    }))
    _unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", json={
        "userId": f"latency-remote-{turn_detection_mode}",
        "bindingId": binding["bindingId"],
        "page": "live",
    }))
    _unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": f"latency-remote-{turn_detection_mode}"}))
    publisher = _unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": f"latency-remote-{turn_detection_mode}",
        "sessionId": session_id,
        "sourceKind": "microphone",
        "clientName": f"remote-probe-{turn_detection_mode}",
    }))

    chunk_size = 3200
    segment_id = f"seg-remote-{turn_detection_mode}-1"
    start_wall = time.time()
    start_ms = int(start_wall * 1000)
    first_partial_wall: int | None = None
    first_partial_revision: int | None = None
    final_wall: int | None = None
    history: list[dict[str, object]] = []

    for idx, offset in enumerate(range(0, len(pcm), chunk_size), start=1):
        target_wall = start_wall + (idx - 1) * 0.1
        now = time.time()
        if target_wall > now:
            time.sleep(target_wall - now)
        chunk = pcm[offset : offset + chunk_size]
        duration_ms = int((len(chunk) / 2 / 16000) * 1000)
        captured_at = start_ms + (idx - 1) * 100
        sent_at = int(time.time() * 1000)
        is_final = offset + chunk_size >= len(pcm)
        _unwrap(client.post("/api/v1/realtime-speech/frames", json={
            "type": "audio-frame",
            "token": publisher["token"],
            "deviceId": f"probe-device-{turn_detection_mode}",
            "sourceId": "mic-default",
            "sequence": idx,
            "sourceKind": "microphone",
            "segmentId": segment_id,
            "revision": idx,
            "capturedAtMs": captured_at,
            "sentAtMs": sent_at,
            "startedAtMs": start_ms,
            "endedAtMs": captured_at + duration_ms,
            "durationMs": duration_ms,
            "codec": "pcm-s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "isFinal": is_final,
            "traceId": f"trace-{turn_detection_mode}-{idx}",
            "audioBase64": base64.b64encode(chunk).decode("ascii"),
        }))
        poll_deadline = time.time() + 0.12
        while time.time() < poll_deadline:
            transcripts = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": f"latency-remote-{turn_detection_mode}"}))
            if transcripts["transcripts"]:
                latest = transcripts["transcripts"][-1]
                if first_partial_wall is None and latest["text"].strip():
                    first_partial_wall = int(time.time() * 1000)
                    first_partial_revision = latest["revision"]
                if latest["isFinal"]:
                    final_wall = int(time.time() * 1000)
                    break
            time.sleep(0.01)
        runtime = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": f"latency-remote-{turn_detection_mode}"}))
        history.append({
            "chunk": idx,
            "isFinalChunk": is_final,
            "timing": (runtime.get("performance") or {}).get("latestBySource", {}).get("microphone"),
            "dominantBottleneck": runtime.get("dominantBottleneck"),
            "stage": runtime.get("stage"),
            "transcriptCount": runtime.get("transcriptCount"),
        })
        if final_wall is not None:
            break

    if final_wall is None:
        deadline = time.time() + 8
        while time.time() < deadline:
            transcripts = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": f"latency-remote-{turn_detection_mode}"}))
            if transcripts["transcripts"] and transcripts["transcripts"][-1]["isFinal"]:
                final_wall = int(time.time() * 1000)
                break
            time.sleep(0.05)

    runtime = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/runtime", params={"userId": f"latency-remote-{turn_detection_mode}"}))
    transcripts = _unwrap(client.get(f"/api/v1/realtime-speech/sessions/{session_id}/transcripts", params={"userId": f"latency-remote-{turn_detection_mode}"}))
    latest_transcript = transcripts["transcripts"][-1] if transcripts["transcripts"] else None
    return {
        "mode": f"remote-{turn_detection_mode}",
        "audioDurationMs": int(len(pcm) / 2 / 16000 * 1000),
        "chunksSent": len(history),
        "firstPartialWallMs": (first_partial_wall - start_ms) if first_partial_wall else None,
        "firstPartialRevision": first_partial_revision,
        "finalWallMs": (final_wall - start_ms) if final_wall else None,
        "runtimeTiming": (runtime.get("performance") or {}).get("latestBySource", {}).get("microphone"),
        "dominantBottleneck": runtime.get("dominantBottleneck"),
        "anomalyReasons": runtime.get("anomalyReasons"),
        "transcriptCount": len(transcripts["transcripts"]),
        "latestTranscript": latest_transcript,
        "historyTail": history[-8:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile OfferSteady live conversation latency.")
    parser.add_argument("--text", default="你好，我正在测试面试稳的实时语音识别。")
    parser.add_argument("--skip-remote", action="store_true")
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "generatedAtMs": int(time.time() * 1000),
        "syntheticInternal": run_synthetic_internal_probe(),
    }
    if not args.skip_remote:
        report["remoteManual"] = run_remote_paced_probe(turn_detection_mode="manual", text=args.text)
        report["remoteVad"] = run_remote_paced_probe(turn_detection_mode="vad", text=args.text)

    output = ARTIFACT_DIR / "live-conversation-latency-profile.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
