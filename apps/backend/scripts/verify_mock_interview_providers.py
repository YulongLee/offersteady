"""Explicit opt-in, synthetic-only checks. Audio remains in memory, never saved.

Run from repo root with PYTHONPATH=apps/backend. Reads existing local settings,
prints only synthetic outputs and timing; does not connect to application DBs.
"""
import argparse
import asyncio
import json
import logging
import sys
from array import array
from time import monotonic

from app.core.config import REPO_ROOT, get_settings
from app.deps import _configured_realtime_asr_gateway
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_generation import MockInterviewGenerator, MockGenerationUnavailable
from app.services.mock_interview_rounds import MockRound
from app.services.mock_interview_tts import MockInterviewTts


async def speech_roundtrip(settings):
    started = monotonic()
    chunks = []
    first_audio = None
    text = "I use a unique constraint to prevent duplicate writes." if settings.product_edition == "global" else "这是一次模拟面试收音测试。我使用唯一约束避免重复写入。"
    async for chunk in MockInterviewTts(settings).stream(text):
        if first_audio is None:
            first_audio = monotonic() - started
        chunks.append(chunk)
    samples = array("h", b"".join(chunks))
    chunks.clear()
    if sys.byteorder != "little": samples.byteswap()
    converted = array("h")
    for index in range(len(samples) * 2 // 3):
        position = index * 1.5
        left = int(position)
        weight = position - left
        converted.append(int(samples[left] * (1-weight) + samples[min(left+1, len(samples)-1)] * weight))
    if sys.byteorder != "little": converted.byteswap()
    # Real microphone input keeps emitting silence when the speaker pauses.
    pcm = converted.tobytes() + b"\0" * 19200
    gateway = _configured_realtime_asr_gateway(settings, logging.getLogger("mock-synthetic-qa"))
    audio = MockInterviewAudio(gateway, interview_language="en-US" if settings.product_edition == "global" else "zh-CN")
    transcripts = []
    capture = audio.open(session_id="mock-synthetic-provider-qa", owner_id="synthetic", device_id="synthetic",
        epoch="a"*32, deadline_ms=audio.now_ms()+120000, sink=lambda epoch, text: transcripts.append(text))
    try:
        for offset in range(0, len(pcm), 3200):
            await asyncio.to_thread(audio.ingest, session_id=capture.session_id, device_id="synthetic",
                epoch=capture.epoch, pcm=pcm[offset:offset+3200])
            await asyncio.sleep(.1)
        await asyncio.sleep(1.5)
        latest = transcripts[-1] if transcripts else ""
        expected = ("unique", "duplicate", "write") if settings.product_edition == "global" else ("唯一约束", "重复", "写入")
        assert all(word in latest.lower() for word in expected), "synthetic transcription did not match"
        return {"tts_first_audio_seconds": round(first_audio, 3), "pcm_seconds": round(len(pcm)/32000, 2),
                "transcript": latest, "updates": len(transcripts), "total_seconds": round(monotonic()-started, 2)}
    finally:
        await asyncio.to_thread(audio.close, audio.revoke(capture.session_id))
        assert audio.snapshot() == {"captures": 0, "draft_characters": 0}
        assert gateway.diagnostics("microphone")["active_provider_sessions"] == 0


async def evaluate(settings):
    generator = MockInterviewGenerator(settings)
    suite = "ai/evals/global-mock-interview-v1.jsonl" if settings.product_edition == "global" else "ai/evals/mock-interview-v1.jsonl"
    cases = [json.loads(line) for line in (REPO_ROOT / suite).read_text().splitlines() if line.strip()]
    output = []
    for case in cases:
        if case.get("published_question_count") == 10 or "provider_question" in case:
            # Covered deterministically by state/output tests; do not pay for an
            # eleventh question or pretend to control a real model's exact output.
            output.append({"id": case["id"], "kind": "deterministic-regression"})
            continue
        rounds = tuple(MockRound(f"q{index+1}", item["question"], item.get("answer")) for index, item in enumerate(case.get("rounds", [])))
        started = monotonic()
        method = generator.report if case.get("operation") == "report" else generator.question
        result = await method(resume=case.get("resume", ""), target_role=case.get("role", ""), rounds=rounds)
        if case.get("operation") == "report":
            for item in result.feedback:
                if settings.product_edition == "global":
                    assert "not a claim about past experience" in item.suggestion
                    assert "unmeasured or unverified" in item.suggestion
                else:
                    assert "不是已经发生的经历" in item.suggestion
                    assert "没有测量或无法确认时明确说明尚未验证" in item.suggestion
        else:
            assert result.question.count("？") + result.question.count("?") <= 1
        output.append({"id": case["id"], "seconds": round(monotonic()-started, 2),
                       "structural_checks": "passed", "semantic_review": "manual-required", "output": result.model_dump()})
    return output


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tts-asr", action="store_true")
    parser.add_argument("--evals", action="store_true")
    args = parser.parse_args()
    if not args.tts_asr and not args.evals:
        parser.error("Explicit --tts-asr or --evals opt-in required")
    settings = get_settings()
    try:
        if args.tts_asr:
            print(json.dumps({"speech": await speech_roundtrip(settings)}, ensure_ascii=False), flush=True)
        if args.evals:
            print(json.dumps({"evals": await evaluate(settings)}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"failed": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    asyncio.run(main())
