"""Synthetic provider contracts only; this does not claim live provider permission."""
import asyncio
import base64
import json
from unittest.mock import Mock

import httpx

from app.core.config import REPO_ROOT, Settings
from app.ports.realtime_speech import TranscriptResult
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_generation import MockInterviewGenerator
from app.services.mock_interview_rounds import MockRound
from app.services.mock_interview_tts import MockInterviewTts
from test_mock_interview_tts import Socket


def test_global_speech_is_explicit_english_and_closes():
    settings = Settings(_env_file=None, product_edition="global", chat_qwen_api_key="synthetic")
    socket = Socket([{"type": "session.updated"},
        {"type": "response.audio.delta", "delta": base64.b64encode(b"\0\0"*100).decode()},
        {"type": "session.finished"}])
    connector = Mock(return_value=socket)
    tts = MockInterviewTts(settings, connector=connector)
    async def run():
        return b"".join([chunk async for chunk in tts.stream("Describe a synthetic project.")])
    assert len(asyncio.run(run())) == 200
    assert connector.call_args.args[0].startswith("wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime?")
    assert socket.sent[0]["session"]["language_type"] == "English"
    assert "English" in socket.sent[0]["session"]["instructions"]
    assert socket.closed
    gateway = Mock()
    gateway.transcribe.return_value = TranscriptResult("Synthetic answer", .9)
    audio = MockInterviewAudio(gateway, now_ms=lambda: 1000, interview_language="en-US")
    capture = audio.open(session_id="synthetic", owner_id="owner", device_id="device", epoch="a"*32,
                         deadline_ms=2000, sink=lambda *_: None)
    try:
        audio.ingest(session_id="synthetic", device_id="device", epoch=capture.epoch, pcm=b"\0\0"*1600)
        assert gateway.transcribe.call_args.kwargs["frame"].interview_language == "en-US"
    finally:
        audio.close(audio.revoke("synthetic"))
    assert audio.snapshot() == {"captures": 0, "draft_characters": 0}


def test_global_tts_endpoint_override_does_not_follow_cn_endpoint():
    settings = Settings(_env_file=None, product_edition="global", chat_qwen_api_key="synthetic",
        mock_interview_tts_ws_url="wss://cn.invalid/realtime",
        global_mock_interview_tts_ws_url="wss://global.invalid/realtime")
    socket = Socket([{"type": "session.updated"},
        {"type": "response.audio.delta", "delta": base64.b64encode(b"\0\0").decode()},
        {"type": "session.finished"}])
    connector = Mock(return_value=socket)
    async def run():
        return [chunk async for chunk in MockInterviewTts(settings, connector=connector).stream("Hello.")]
    asyncio.run(run())
    assert connector.call_args.args[0].startswith("wss://global.invalid/realtime?")


def test_english_question_and_evidence_checked_report_contract():
    cases = [json.loads(line) for line in (REPO_ROOT / "ai/evals/global-mock-interview-v1.jsonl").read_text().splitlines()]
    for case in cases:
        requests = []
        def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(case["synthetic_provider_response"])}}]})
        service = MockInterviewGenerator(Settings(_env_file=None, product_edition="global",
            chat_qwen_api_key="synthetic", chat_qwen_base_url="https://synthetic.invalid/v1"),
            transport=httpx.MockTransport(handle))
        rounds = tuple(MockRound(**r) for r in case["rounds"])
        method = service.report if case["operation"] == "report" else service.question
        result = asyncio.run(method(resume=case["resume"], target_role="Backend engineer", rounds=rounds))
        assert requests[0]["enable_thinking"] is False
        assert "English" in requests[0]["messages"][0]["content"]
        if case["operation"] == "report":
            assert result.overall_score == 65
            assert result.summary.startswith("Partial report (1/10")
            assert "not a claim about past experience" in result.feedback[0].suggestion
            assert "saved a million" not in result.feedback[0].suggestion
        else:
            assert result.question.count("?") == 1
