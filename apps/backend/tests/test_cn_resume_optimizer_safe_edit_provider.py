"""Synthetic safe-edit selection, strict global gates and truthful delivery."""
from copy import deepcopy
from itertools import permutations
import json

import pytest

from app.core.config import REPO_ROOT
from app.services.cn_resume_optimizer_provider import (
    PROMPT_VERSION, ResumeProviderError, validate_resume_review,
)
from cn_resume_optimizer_test_support import QUOTE, RESUME, review_payload


SAFE = {"sourceQuote": QUOTE, "replacement": "使用Python实现数据接口开发"}
PRIVATE = "SYNTHETIC_REJECTED_REPLACEMENT_SENTINEL"


def evaluate(edits, *, resume=RESUME):
    raw = review_payload(edits=False)
    raw["edits"] = deepcopy(edits)
    before = deepcopy(raw)
    result = validate_resume_review(raw, resume=resume, jd="")
    assert raw == before
    return result


def assert_summary(review, *, proposed, applied, fact=0, source=0, overlap=0, unchanged=0):
    assert review["editSummary"] == {"proposedCount": proposed, "appliedCount": applied,
        "retainedCount": proposed - applied, "retainedReasonCounts": {
            "factCheck": fact, "sourceQuote": source, "overlap": overlap, "unchanged": unchanged}}
    summary = review["editSummary"]
    assert set(summary) == {"proposedCount", "appliedCount", "retainedCount", "retainedReasonCounts"}
    assert all(type(v) is int and 0 <= v <= 24 for k,v in summary.items() if k != "retainedReasonCounts")
    assert sum(summary["retainedReasonCounts"].values()) == summary["retainedCount"]


@pytest.mark.parametrize("bad", [
    {"sourceQuote": QUOTE, "replacement": "使用Python和" + PRIVATE + "实现数据接口开发"},
    {"sourceQuote": QUOTE, "replacement": "<script>" + PRIVATE + "</script>"},
    {"sourceQuote": QUOTE, "replacement": PRIVATE + "\x00"},
    {"sourceQuote": QUOTE, "replacement": " \n\t"},
])
def test_rejected_proposal_never_discards_independent_safe_edit_or_leaks(bad):
    review, draft = evaluate([bad, SAFE])
    assert_summary(review, proposed=2, applied=1, fact=1)
    assert SAFE["replacement"] in draft
    assert PRIVATE not in json.dumps(review, ensure_ascii=False) + draft


@pytest.mark.parametrize("control", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f"])
@pytest.mark.parametrize("edge", ["prefix", "suffix"])
def test_fragment_edge_controls_are_rejected_before_strip_without_losing_safe_edit(control, edge):
    replacement = "为12个团队提供相关服务"
    replacement = control + replacement if edge == "prefix" else replacement + control
    bad = {"sourceQuote": "为12个团队提供服务", "replacement": replacement}
    review, draft = evaluate([SAFE, bad])
    assert_summary(review, proposed=2, applied=1, fact=1)
    assert SAFE["replacement"] in draft
    assert "为12个团队提供服务" in draft and control not in draft
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([bad])
    assert caught.value.diagnostic["reason"] == "draft_invalid"


@pytest.mark.parametrize("bad_quote,source", [
    ("不存在的原文引文", RESUME), ("Python", RESUME + "\nPython"),
])
def test_nonunique_or_missing_quote_is_counted_separately(bad_quote, source):
    review, draft = evaluate([{"sourceQuote": bad_quote, "replacement": "安全格式的措辞"}, SAFE], resume=source)
    assert_summary(review, proposed=2, applied=1, source=1)
    assert SAFE["replacement"] in draft


def test_all_four_groups_are_mutually_exclusive_and_only_counts_escape():
    source = RESUME + "\n记录资料处理步骤并整理问题清单。"
    edits = [SAFE,
        {"sourceQuote": QUOTE, "replacement": "使用Python和" + PRIVATE + "实现数据接口开发"},
        {"sourceQuote": "不存在的原文", "replacement": "调整原文措辞"},
        {"sourceQuote": "Python", "replacement": "python"},
        {"sourceQuote": "记录资料处理步骤", "replacement": "整理资料处理步骤"},
        {"sourceQuote": "资料处理步骤并整理", "replacement": "资料处理步骤及整理"}]
    review, draft = evaluate(edits, resume=source)
    assert_summary(review, proposed=6, applied=1, fact=1, source=1, overlap=2, unchanged=1)
    assert "记录资料处理步骤并整理问题清单。" in draft
    assert PRIVATE not in json.dumps(review) + draft


def test_every_member_of_an_overlap_chain_is_removed_for_all_input_orders():
    source = RESUME + "\n记录资料处理步骤并整理问题清单。"
    edits = [SAFE,
        {"sourceQuote": "记录资料处理步骤", "replacement": "整理资料处理步骤"},
        {"sourceQuote": "资料处理步骤并整理", "replacement": "资料处理步骤及整理"},
        {"sourceQuote": "并整理问题清单", "replacement": "并维护问题清单"}]
    outputs = []
    for ordered in permutations(edits):
        review, draft = evaluate(ordered, resume=source)
        assert_summary(review, proposed=4, applied=1, overlap=3)
        outputs.append((review, draft))
    assert all(output == outputs[0] for output in outputs)
    assert "记录资料处理步骤并整理问题清单。" in outputs[0][1]


def test_adjacent_spans_are_not_overlapping():
    source = RESUME + "\n负责文档整理记录处理步骤"
    review, draft = evaluate([
        {"sourceQuote": "负责文档整理", "replacement": "承担文档整理"},
        {"sourceQuote": "记录处理步骤", "replacement": "整理处理步骤"}], resume=source)
    assert_summary(review, proposed=2, applied=2)
    assert "承担文档整理整理处理步骤" in draft


@pytest.mark.parametrize("edits", [[],
    [{"sourceQuote": QUOTE, "replacement": QUOTE}],
    [{"sourceQuote": QUOTE, "replacement": "  " + QUOTE + "。  "}],
    [{"sourceQuote": "Python", "replacement": "python"}],
    [{"sourceQuote": "Python", "replacement": "Python\u200b"}],
])
def test_empty_or_only_cosmetic_edits_cannot_be_delivered(edits):
    with pytest.raises(ResumeProviderError) as caught:
        evaluate(edits)
    assert caught.value.category == "invalid_output"
    assert caught.value.diagnostic == {"stage": "draft", "reason": "no_effective_edits"}


def test_safe_noop_does_not_participate_in_overlap_graph():
    review, draft = evaluate([{"sourceQuote": "Python", "replacement": "python"}, SAFE])
    assert_summary(review, proposed=2, applied=1, unchanged=1)
    assert SAFE["replacement"] in draft


def test_first_nonnoop_rejection_is_kept_even_when_a_noop_comes_first():
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([{"sourceQuote": "Python", "replacement": "Python"},
            {"sourceQuote": QUOTE, "replacement": "使用Kubernetes开发数据接口"},
            {"sourceQuote": "没有的原文", "replacement": "整理原文"}])
    assert caught.value.diagnostic["reason"] == "fact_english_content_added"


def test_overlap_rejection_can_precede_later_fact_rejection_in_original_order():
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([SAFE,
            {"sourceQuote": "12个团队", "replacement": "30个团队"},
            {"sourceQuote": "开发数据接口", "replacement": "实现数据接口开发"}])
    assert caught.value.diagnostic["reason"] == "edit_spans_overlap"


def test_all_bad_does_not_clear_edits_or_return_original_as_success():
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([{"sourceQuote": "12个团队", "replacement": "30个团队"},
            {"sourceQuote": QUOTE, "replacement": "主导Kubernetes开发"}])
    assert caught.value.diagnostic["reason"] == "fact_numbers_changed"


def test_individually_changed_spans_that_cancel_globally_are_not_effective():
    source = RESUME + "\n甲乙\n丙丁"
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([{"sourceQuote": "甲乙", "replacement": "甲"},
                  {"sourceQuote": "丙丁", "replacement": "乙丙丁"}], resume=source)
    assert caught.value.diagnostic["reason"] == "no_effective_edits"


def test_replacement_is_not_stripped_when_applied_inside_document():
    replacement = "  使用Python实现数据接口开发  "
    review, draft = evaluate([{"sourceQuote": QUOTE, "replacement": replacement}])
    assert_summary(review, proposed=1, applied=1)
    assert replacement in draft


def test_maximum_proposals_remain_bounded_and_counted():
    review, _ = evaluate([SAFE] + [{"sourceQuote": "Python", "replacement": "python"}] * 23)
    assert_summary(review, proposed=24, applied=1, unchanged=23)
    with pytest.raises(ResumeProviderError) as caught:
        evaluate([SAFE] * 25)
    assert caught.value.diagnostic["reason"] == "review_schema_invalid"


@pytest.mark.parametrize("mutation,reason", [
    (lambda raw: raw["suggestions"][0]["evidence"][0].update(quote="虚假依据"), "evidence_quote_missing"),
    (lambda raw: raw["dimensions"][0].update(score=101), "review_schema_invalid"),
    (lambda raw: raw["suggestions"][0].update(title="English only"), "explanation_language_invalid"),
    (lambda raw: raw.update(editSummary={"appliedCount": 10}), "review_schema_invalid"),
    (lambda raw: raw["edits"].append({"sourceQuote": QUOTE, "replacement": "安全内容", "extra": PRIVATE}), "review_schema_invalid"),
])
def test_global_invalidity_never_partially_delivers(mutation, reason):
    raw = review_payload()
    mutation(raw)
    with pytest.raises(ResumeProviderError) as caught:
        validate_resume_review(raw, resume=RESUME, jd="")
    assert caught.value.diagnostic["reason"] == reason


def test_final_document_length_is_still_a_global_failure():
    markers = "甲乙丙丁戊己庚辛壬癸"
    source = RESUME + "\n" + "啊" * 39000 + "\n" + "\n".join("记录条目" + marker for marker in markers)
    edits = [{"sourceQuote": "记录条目" + marker, "replacement": "整理" + marker + "内容" * 1100} for marker in markers]
    with pytest.raises(ResumeProviderError) as caught:
        evaluate(edits, resume=source)
    assert caught.value.diagnostic["reason"] == "draft_invalid"


@pytest.mark.parametrize("location", ["same_paragraph", "different_project"])
def test_content_word_outside_exact_quote_is_not_borrowed(location):
    quote = "负责Java接口开发"
    context = quote + ("，配套服务使用SpringBoot。" if location == "same_paragraph" else "。\n\n另一项目使用SpringBoot。")
    review, draft = evaluate([{"sourceQuote": quote, "replacement": "负责Java和SpringBoot接口开发"}, SAFE], resume=RESUME + "\n" + context)
    assert_summary(review, proposed=2, applied=1, fact=1)
    assert context in draft


@pytest.mark.parametrize("quote,replacement", [
    ("负责使用SpringBoot开发业务接口", "使用SpringBoot实现业务接口开发"),
    ("负责维护REST API的请求参数说明", "维护REST API的请求参数说明"),
    ("负责使用Python-based脚本处理数据", "使用Python-based脚本完成数据处理"),
    ("负责中文接口的资料查询开发", "承担中文接口的资料查询开发"),
])
def test_same_quote_content_tokens_stay_unchanged_in_valid_chinese_rewrite(quote,replacement):
    review, draft = evaluate([{"sourceQuote": quote, "replacement": replacement}], resume=RESUME + "\n" + quote)
    assert_summary(review, proposed=1, applied=1)
    assert replacement in draft


def test_prompt_v2_is_explicit_and_original_prompt_stays_available():
    prompt = (REPO_ROOT / "ai/prompts/resume-optimizer/review.zh-CN.v2.md").read_text()
    assert PROMPT_VERSION == "resume-optimizer-zh-CN-v2"
    for required in ["sourceQuote", "同一段落", "SpringBoot", "REST API", "Python-based", "不是候选人事实", "不算有效优化", "editSummary", "evidence 数组1–4条"]:
        assert required in prompt
    assert (REPO_ROOT / "ai/prompts/resume-optimizer/review.zh-CN.v1.md").exists()


CASES = [json.loads(line) for line in
    (REPO_ROOT / "ai/evals/cn-resume-optimizer-safe-edits-v2.jsonl").read_text().splitlines() if line.strip()]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_safe_edit_offline_evals(case):
    assert case["synthetic"] is True
    if case["expectedAccepted"]:
        review, draft = validate_resume_review(case["output"], resume=case["resume"], jd=case["jd"])
        assert review["editSummary"] == case["expectedSummary"]
        assert draft == case["expectedDraft"]
        for expected in case.get("expectedContains", []):
            assert expected in draft
        for rejected in case.get("expectedAbsent", []):
            assert rejected not in draft + json.dumps(review, ensure_ascii=False)
    else:
        with pytest.raises(ResumeProviderError) as caught:
            validate_resume_review(case["output"], resume=case["resume"], jd=case["jd"])
        assert caught.value.diagnostic["reason"] == case["expectedReason"]
