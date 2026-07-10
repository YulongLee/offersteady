from __future__ import annotations

import argparse
import io
import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _ms() -> float:
    return time.perf_counter() * 1000


def _unwrap(payload: dict[str, Any]) -> Any:
    if payload.get("success") is not True and payload.get("ok") is not True:
        raise RuntimeError(payload)
    return payload.get("data")


def _request_json(base_url: str, method: str, path: str, body: dict[str, Any] | None = None, query: dict[str, str] | None = None, timeout: int = 120) -> Any:
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _unwrap(json.loads(response.read().decode("utf-8")))


def _request_multipart(base_url: str, path: str, fields: dict[str, str], filename: str, content_type: str, content: bytes, timeout: int = 120) -> Any:
    boundary = "----OfferSteadyPerf" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="screenshot"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode())
    chunks.append(content)
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    data = b"".join(chunks)
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(data))},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _unwrap(json.loads(response.read().decode("utf-8")))


def _compress_like_desktop(payload: bytes) -> tuple[tuple[int, int] | None, tuple[int, int] | None, bytes]:
    settings = get_settings()
    try:
        from PIL import Image
    except Exception:
        return None, None, payload
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        original_size = image.size
        longest = max(original_size)
        max_edge = int(settings.screenshot_vision_max_long_edge)
        if longest > max_edge:
            ratio = max_edge / float(longest)
            image = image.resize((max(1, round(original_size[0] * ratio)), max(1, round(original_size[1] * ratio))), Image.Resampling.LANCZOS)
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGB", image.size, (255, 255, 255))
            rgba = image.convert("RGBA")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=int(settings.screenshot_vision_jpeg_quality), optimize=True, progressive=True)
        return original_size, image.size, output.getvalue()


def _timed(metrics: list[dict[str, Any]], stage: str, fn):
    started = _ms()
    result = fn()
    metrics.append({"stage": stage, "ms": round(_ms() - started, 2)})
    return result


def run(image_path: Path, *, base_url: str, output_dir: Path) -> dict[str, Any]:
    user_id = f"perf-user-{uuid.uuid4().hex[:8]}"
    device_id = f"perf-device-{uuid.uuid4().hex[:8]}"
    manual_code = str(200000 + int(uuid.uuid4().hex[:4], 16) % 700000)
    metrics: list[dict[str, Any]] = []
    started = _ms()

    raw = _timed(metrics, "read_image", image_path.read_bytes)
    original_size, compressed_size, jpeg = _timed(metrics, "desktop_compress_jpeg", lambda: _compress_like_desktop(raw))
    session = _timed(metrics, "create_session", lambda: _request_json(base_url, "POST", "/api/v1/sessions", {"userId": user_id, "title": "截屏回答性能自测"}))
    session_id = session["sessionId"]
    _timed(metrics, "register_desktop", lambda: _request_json(base_url, "POST", "/api/v1/realtime-speech/desktop-devices/register", {
        "deviceId": device_id,
        "manualCode": manual_code,
        "displayName": "Perf Desktop",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }))
    binding = _timed(metrics, "bind_desktop", lambda: _request_json(base_url, "POST", f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", {"userId": user_id, "manualCode": manual_code}))
    _timed(metrics, "web_heartbeat", lambda: _request_json(base_url, "POST", f"/api/v1/realtime-speech/sessions/{session_id}/web-heartbeat", {"userId": user_id, "bindingId": binding["bindingId"], "page": "live"}))
    _timed(metrics, "start_interview", lambda: _request_json(base_url, "POST", f"/api/v1/sessions/{session_id}/start", {"userId": user_id}))
    created = _timed(metrics, "create_remote_capture_request", lambda: _request_json(base_url, "POST", f"/api/v1/screenshot-answer/sessions/{session_id}/remote-capture-requests", {"userId": user_id, "instruction": "请根据截图识别题目并给出答案，代码题必须给完整代码。"}))
    request_id = created["requestId"]
    _timed(metrics, "desktop_fetch_request", lambda: _request_json(base_url, "GET", f"/api/v1/screenshot-answer/desktop-devices/{device_id}/capture-requests/next", query={"manualCode": manual_code}))
    upload_started = _ms()
    upload_response = _timed(metrics, "desktop_upload_return", lambda: _request_multipart(base_url, f"/api/v1/screenshot-answer/capture-requests/{request_id}/desktop-upload", {"deviceId": device_id, "manualCode": manual_code}, "screenshot.jpg", "image/jpeg", jpeg))
    upload_return_ms = round(_ms() - upload_started, 2)

    loaded = None
    polls = 0
    poll_started = _ms()
    while _ms() - poll_started < 240000:
        polls += 1
        loaded = _request_json(base_url, "GET", f"/api/v1/screenshot-answer/capture-requests/{request_id}", query={"userId": user_id}, timeout=30)
        if loaded.get("status") in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.5)
    poll_total_ms = round(_ms() - poll_started, 2)
    answer_task = (loaded or {}).get("answerTask") or {}
    telemetry = (loaded or {}).get("telemetry") or {}
    task_telemetry = answer_task.get("telemetry") or {}
    combined_telemetry = {**telemetry, **task_telemetry}
    model_ms = float(combined_telemetry.get("visionModelMs") or 0)
    controllable_ms = max(0.0, float(combined_telemetry.get("totalBackgroundMs") or 0) - model_ms)

    report = {
        "imagePath": str(image_path),
        "requestId": request_id,
        "sessionId": session_id,
        "taskId": answer_task.get("taskId"),
        "originalBytes": len(raw),
        "compressedBytes": len(jpeg),
        "originalSize": original_size,
        "compressedSize": compressed_size,
        "uploadReturn": {"status": upload_response.get("status"), "stage": upload_response.get("stage"), "ms": upload_return_ms},
        "finalResult": {
            "status": (loaded or {}).get("status"),
            "stage": (loaded or {}).get("stage"),
            "polls": polls,
            "pollTotalMs": poll_total_ms,
            "answerTaskStatus": answer_task.get("status"),
            "visionProviderName": answer_task.get("visionProviderName"),
            "visionModelName": answer_task.get("visionModelName"),
            "retrievalExcerptCount": answer_task.get("retrievalExcerptCount"),
            "materialContextStatus": answer_task.get("materialContextStatus"),
            "errorCode": answer_task.get("errorCode"),
        },
        "telemetry": combined_telemetry,
        "metrics": metrics,
        "summary": {
            "timeToNonBlockingUploadReturnMs": upload_return_ms,
            "totalUntilFinalMs": round(_ms() - started, 2),
            "modelApiMs": model_ms,
            "controllableEngineeringMs": round(controllable_ms, 2),
            "remainingOptimization": "模型 API 耗时不在本次优化范围内；可继续优化 OSS 写入、前端阶段提示和后台队列可靠性。",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"screenshot-answer-perf-{int(time.time() * 1000)}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["reportPath"] = str(output_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OfferSteady screenshot answer performance self-test.")
    parser.add_argument("image", type=Path, help="Local screenshot image path.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL without /api/v1.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/perf"))
    args = parser.parse_args()
    report = run(args.image, base_url=args.base_url, output_dir=args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
