import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services.mock_interview_generation import MockGenerationUnavailable, MockInterviewGenerator, MockResumeReader
from app.services.mock_interview_rounds import MockRound


def settings():
    return Settings(_env_file=None, chat_qwen_api_key="synthetic-key", chat_qwen_base_url="https://synthetic.invalid/v1")


def generator(payload, *, finish_reason="stop"):
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": finish_reason,
                              "message": {"content": json.dumps(payload, ensure_ascii=False)}}]})
    return MockInterviewGenerator(settings(), transport=httpx.MockTransport(handle)), requests


def feedback_payload():
    return {"summary": "有诊断思路，可以增加验证步骤。", "dimensions": {"relevance": 80, "clarity": 70, "depth": 60, "evidence": 50},
            "feedback": [{"question_id": "q1", "answer_quote": "先看错误率", "strength": "有明确入口",
                          "improvement": "尚未说明验证方法", "suggestion": "补充【请补充真实例子】中的验证步骤"}],
            "practice_priorities": ["练习闭环验证"]}


def test_question_context_is_structured_non_thinking_and_independent():
    service, requests = generator({"question": "你如何保证订单幂等？", "focus": "幂等设计"})
    answer = asyncio.run(service.question(resume="合成订单项目", target_role="后端", rounds=()))
    assert answer.focus == "幂等设计"
    assert requests[0]["enable_thinking"] is False
    assert requests[0]["stream"] is False
    assert json.loads(requests[0]["messages"][1]["content"])["resume"] == "合成订单项目"
    assert "不可信资料" in requests[0]["messages"][0]["content"]


@pytest.mark.parametrize("payload,finish", [
    ({"question": "", "focus": "测试"}, "stop"),
    ({"question": "正常题目", "focus": "测试", "score": 100}, "stop"),
    ({"question": "正常题目", "focus": "测试"}, "length"),
])
def test_invalid_or_truncated_question_is_not_published(payload, finish):
    service, _ = generator(payload, finish_reason=finish)
    with pytest.raises(MockGenerationUnavailable):
        asyncio.run(service.question(resume="合成", target_role="", rounds=()))


def test_no_unanswered_or_eleventh_question_provider_call():
    service, requests = generator({"question": "测试", "focus": "测试"})
    for rounds in [(MockRound("q", "还没回答"),), tuple(MockRound(str(i), f"问题{i}", "合成回答") for i in range(10))]:
        with pytest.raises(MockGenerationUnavailable):
            asyncio.run(service.question(resume="合成", target_role="", rounds=rounds))
    assert requests == []


def test_no_answer_report_has_no_score_or_provider_call():
    service, requests = generator({})
    report = asyncio.run(service.report(resume="合成", target_role="", rounds=(MockRound("q", "未答问题"),)))
    assert report.overall_score is None and report.feedback == []
    assert requests == []


def test_model_appended_followup_is_not_published_as_second_question():
    service, _ = generator({"question": "如何保证订单幂等？是使用唯一键还是状态机？", "focus": "幂等"})
    result = asyncio.run(service.question(resume="合成", target_role="后端", rounds=()))
    assert result.question == "如何保证订单幂等？"


def test_model_invented_results_are_not_used_as_sample_answer():
    payload = feedback_payload()
    payload["feedback"][0]["suggestion"] = "我把错误率从5%降低到0%，用户反馈速度明显提升。"
    service, _ = generator(payload)
    report = asyncio.run(service.report(resume="合成", target_role="后端",
        rounds=(MockRound("q1", "如何验证效果？", "先看错误率，但没有正式测量结果。"),)))
    suggestion = report.feedback[0].suggestion
    assert "先看错误率" in suggestion
    assert "5%" not in suggestion and "速度明显提升" not in suggestion
    assert "没有测量或无法确认时明确说明尚未验证" in suggestion


def test_report_quotes_actual_answer_and_computes_score():
    service, requests = generator(feedback_payload())
    report = asyncio.run(service.report(resume="合成", target_role="", rounds=(MockRound("q1", "怎样定位？", "我会先看错误率再检查日志。"), MockRound("q2", "未答问题"))))
    assert report.overall_score == 65
    assert "已回答 1/10" in report.summary
    assert len(json.loads(requests[0]["messages"][1]["content"])["rounds"]) == 1


@pytest.mark.parametrize("mutation", ["quote", "id", "duplicate", "score", "extra"])
def test_report_rejects_fabricated_evidence_and_bad_dimensions(mutation):
    payload = feedback_payload()
    if mutation == "quote": payload["feedback"][0]["answer_quote"] = "模型编造的内容"
    if mutation == "id": payload["feedback"][0]["question_id"] = "other-user-question"
    if mutation == "duplicate": payload["feedback"].append(payload["feedback"][0])
    if mutation == "score": payload["dimensions"]["evidence"] = 999
    if mutation == "extra": payload["personality"] = "不应推断人格"
    service, _ = generator(payload)
    with pytest.raises(MockGenerationUnavailable):
        asyncio.run(service.report(resume="合成", target_role="", rounds=(MockRound("q1", "问题", "先看错误率。"),)))


def reader(**changes):
    doc = dict(document_id="resume-synthetic", owner_user_id="synthetic-owner", document_kind="resume", status="ready",
               index_state="indexed", deleted_at_ms=None, document_version_id="v1", summary="这是不可使用的短摘要")
    doc.update(changes)
    calls = []
    def load(**kw):
        calls.append(kw)
        return ("合成项目正文。邮箱 test@example.invalid，手机 13800000000。" + "实际项目细节。" * 300).encode()
    return MockResumeReader(settings(), SimpleNamespace(get_by_id=lambda _: SimpleNamespace(**doc)),
                            SimpleNamespace(load_object_bytes=load)), calls


def test_resume_reads_parsed_body_not_short_summary_and_redacts_contacts():
    service, calls = reader()
    content = service.read(user_id="synthetic-owner", document_id="resume-synthetic", version_id="v1")
    assert "实际项目细节" in content and len(content) > 900
    assert "短摘要" not in content and "13800000000" not in content and "test@example.invalid" not in content
    assert calls[0]["object_key"].endswith("/processed/normalized.md")


@pytest.mark.parametrize("change", [{"owner_user_id": "other"}, {"status": "processing"},
                                      {"deleted_at_ms": 1}, {"document_version_id": "v2"}, {"document_kind": "knowledge"}])
def test_resume_rejects_unowned_unavailable_or_changed_version_before_storage(change):
    service, calls = reader(**change)
    with pytest.raises(DomainRequestError):
        service.read(user_id="synthetic-owner", document_id="resume-synthetic", version_id="v1")
    assert calls == []


def test_resume_context_is_bounded():
    service, _ = reader()
    service.max_characters = 100
    content = service.read(user_id="synthetic-owner", document_id="resume-synthetic", version_id="v1")
    assert len(content) < 130 and "已截断" in content
