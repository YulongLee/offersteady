"""Isolated, bounded resume provider and conservative evidence validation."""
from __future__ import annotations

from collections import Counter
import json
import math
import re

import httpx
from pydantic import ValidationError

from app.core.config import REPO_ROOT, Settings
from app.schemas.cn_resume_optimizer import ProviderResumeReview
from app.services.cn_resume_optimizer_diagnostics import failure_diagnostic

PROMPT_VERSION = "resume-optimizer-zh-CN-v2"
SCORE_VERSION = "resume-reference-v1"
DISCLAIMER = "评分仅供本工具简历评估参考，不代表录用概率。使用前请逐项核实所有事实。"


class ResumeProviderError(Exception):
    """Only fixed labels, never a provider response or document excerpt."""
    def __init__(self, category="invalid_output", *, reason=None):
        self.category = category if type(category) is str and category in {"invalid_output", "provider_timeout", "provider_unavailable", "provider_unconfigured", "interrupted", "source_unavailable"} else "invalid_output"
        self.diagnostic = failure_diagnostic(reason)
        super().__init__(self.category)


def validate_plain_text(text: str) -> str:
    value = text.strip()
    if (not value or len(value) > 60000
            or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value)
            or re.search(r"</?[A-Za-z][^>]*>", value)):
        raise ResumeProviderError(reason="draft_invalid")
    return value


def _chinese(text: str) -> bool:
    letters=[c for c in text if c.isalpha()]
    chinese=sum("\u3400"<=c<="\u9fff" for c in letters)
    return chinese>=2 and chinese/max(1,len(letters))>=.15


# Only grammatical/connective words and conservative task wording may be novel.
# Content-bearing nouns, technologies, employers and unsupported achievements must
# already exist in the resume. This intentionally rejects ambitious rewrites.
_SAFE_WORDS = set("""a an the and or but for to of in on at by with from as into through within across using used use uses
that which who whose is are was were be been being has have had its their this these those it they we i my our
worked working work developed developing develop built build building created creating create implemented implementing implement
maintained maintaining maintain supported supporting support improved improving improve helped helping help assisted assisting assist
contributed contributing contribute collaborated collaborating collaborate designed designing design managed managing manage
responsible responsibility responsibilities delivered delivering deliver performed performing perform wrote writing write
organized organizing organize tested testing test reviewed reviewing review documented documenting document
tracked tracking track prepared preparing prepare provided providing provide enabled enabling enable
ensured ensuring ensure coordinated coordinating coordinate participated participating participate
including include includes included while during then also both each all other more clear clearly effectively
""".split())
_WORDS = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]*")
_NUMBERS = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,:/-]\d+)*(?:\s?%)?")
_CONTACT = re.compile(r"https?://[^\s)]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)\+?\d[\d ()-]{6,}\d(?!\d)")
_LIMITED_AGENCY = re.compile(r"\b(helped|assisted|supported|contributed|participated)\b", re.I)
_STRONG_AGENCY = re.compile(r"\b(led|lead|owned|spearheaded|directed|architected|managed|designed|improved|ensured|enabled|expert|senior|principal|certified)\b", re.I)


# Narrow lexical checks supplement the Chinese prompt; they cannot prove all
# semantic factual fidelity. Ordinary Chinese sentence edits remain permitted.
_CN_CREDENTIALS = re.compile(r"博士后|博士|硕士|研究生|本科|学士|专科|大专|中专|高中|初中|双一流|结业|肄业|在读|实习|助理|兼职")
_CN_DATES_COUNTS = re.compile(r"(?:[零〇一二三四五六七八九十百千万亿两\d]+(?:年|月|日|岁|个人|人|个|倍|万元|亿元|万|亿|项|次|套|台|条|%|％)|百分之[零〇一二三四五六七八九十百\d]+|周[一二三四五六日天])")
_CN_NEGATION = re.compile(r"未曾|从未|没有|尚未|不能|无法|未能|不具备|未|无|不")
_CN_LIMITED = re.compile(r"参与|协助|辅助|配合|支持")
_CN_STRONG = re.compile(r"主导|领导|带领|牵头|独立|全权|负责人|架构师|专家|高级|资深|精通|熟练掌握")
_CN_ENTITIES = re.compile(r"[\u3400-\u9fffA-Za-z0-9·&（）()_-]{1,40}(?:有限责任公司|股份有限公司|有限公司|公司|集团|大学|学院|研究院|研究所|实验室|银行|医院)")
_ENTITY_PREFIX = re.compile(r"^(?:(?:曾|现)?(?:毕业于|就读于|任职于|就职于|供职于|就职|任职|毕业|就读|进入|加入|入职|来自)|学校为|公司为|负责|承担|担任|在|于|从)")
_CN_SKILLS = ("机器学习","深度学习","自然语言处理","计算机视觉","强化学习","分布式","微服务","云原生","容器编排","大模型","数据仓库","数据湖","推荐算法","推荐系统","高并发","高可用","负载均衡","消息队列","区块链","数据分析","数据挖掘","数仓","全栈","编译器","操作系统","网络安全","渗透测试","自动化测试","运维","集群")


def _entity_tokens(text):
    tokens=[]
    for match in _CN_ENTITIES.finditer(text):
        value=match.group()
        value=re.sub(r"^[零〇一二三四五六七八九十百千万亿两\d]+年(?:[零〇一二三四五六七八九十两\d]+月)?", "", value)
        while True:
            changed=_ENTITY_PREFIX.sub("",value,count=1)
            if changed==value:
                break
            value=changed
        tokens.append(value)
    return Counter(tokens)


def _validate_chinese_edit(quote,replacement):
    for rule,reason in ((_CN_CREDENTIALS,"fact_credentials_changed"),
                        (_CN_DATES_COUNTS,"fact_dates_counts_changed"),
                        (_CN_NEGATION,"fact_negation_changed")):
        if Counter(rule.findall(quote))!=Counter(rule.findall(replacement)):
            raise ResumeProviderError(reason=reason)
    if _entity_tokens(quote)!=_entity_tokens(replacement):
        raise ResumeProviderError(reason="fact_entities_changed")
    if _CN_LIMITED.search(quote) and not _CN_LIMITED.search(replacement):
        raise ResumeProviderError(reason="fact_responsibility_changed")
    original=Counter(_CN_STRONG.findall(quote))
    if any(count>original[word] for word,count in Counter(_CN_STRONG.findall(replacement)).items()):
        raise ResumeProviderError(reason="fact_responsibility_changed")
    for skill in _CN_SKILLS:
        if replacement.count(skill)!=quote.count(skill):
            raise ResumeProviderError(reason="fact_skills_changed")


def _substantive_text(text):
    # This is only an effectiveness comparison, never a fact/quote normalizer.
    return "".join(character for character in text.casefold() if character.isalnum())


def _validate_edit_span(quote, replacement, *, resume):
    if resume.count(quote) != 1:
        raise ResumeProviderError(reason="edit_quote_not_unique")
    # strip() in the shared whole-document validator can hide edge controls.
    # Fragments are applied verbatim, so inspect their original bytes first.
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", replacement):
        raise ResumeProviderError(reason="draft_invalid")
    # Check the proposed fragment without substituting its stripped return value.
    validate_plain_text(replacement)
    if Counter(_NUMBERS.findall(quote)) != Counter(_NUMBERS.findall(replacement)):
        raise ResumeProviderError(reason="fact_numbers_changed")
    if Counter(_CONTACT.findall(quote)) != Counter(_CONTACT.findall(replacement)):
        raise ResumeProviderError(reason="fact_contact_changed")
    quote_words = Counter(w.rstrip(".-").lower() for w in _WORDS.findall(quote))
    replacement_words = Counter(w.rstrip(".-").lower() for w in _WORDS.findall(replacement))
    if any(word not in quote_words and word not in _SAFE_WORDS for word in replacement_words):
        raise ResumeProviderError(reason="fact_english_content_added")
    if any(replacement_words[word] < count for word,count in quote_words.items() if word not in _SAFE_WORDS):
        raise ResumeProviderError(reason="fact_english_content_removed")
    _validate_chinese_edit(quote,replacement)
    if _LIMITED_AGENCY.search(quote) and not _LIMITED_AGENCY.search(replacement):
        raise ResumeProviderError(reason="fact_responsibility_changed")
    if any(word.lower() not in quote.lower() for word in _STRONG_AGENCY.findall(replacement)):
        raise ResumeProviderError(reason="fact_responsibility_changed")
    start = resume.index(quote)
    return start, start + len(quote), replacement


def _safe_edit_draft(edits, *, resume):
    counts = {"factCheck": 0, "sourceQuote": 0, "overlap": 0, "unchanged": 0}
    candidates, rejections = [], []
    for index, edit in enumerate(edits):
        try:
            span = _validate_edit_span(edit.source_quote, edit.replacement, resume=resume)
        except ResumeProviderError as error:
            reason = error.diagnostic["reason"] if error.diagnostic else None
            group = "sourceQuote" if reason == "edit_quote_not_unique" else "factCheck"
            counts[group] += 1
            # Keep only fixed labels, not rejected objects or their tracebacks.
            rejections.append((index, error.category, reason))
            continue
        if _substantive_text(edit.source_quote) == _substantive_text(edit.replacement):
            counts["unchanged"] += 1
            continue
        candidates.append((index, *span))

    overlapping = set()
    for offset, (index, start, end, _) in enumerate(candidates):
        for other_index, other_start, other_end, _ in candidates[offset + 1:]:
            if start < other_end and end > other_start:
                overlapping.update((index, other_index))
    counts["overlap"] = len(overlapping)
    rejections.extend((index, "invalid_output", "edit_spans_overlap") for index in overlapping)
    spans = [(start, end, replacement) for index, start, end, replacement in candidates
             if index not in overlapping]
    if not spans:
        if rejections:
            _, category, reason = min(rejections, key=lambda rejection: rejection[0])
            raise ResumeProviderError(category, reason=reason)
        raise ResumeProviderError(reason="no_effective_edits")

    draft = resume
    for start, end, replacement in sorted(spans, reverse=True):
        draft = draft[:start] + replacement + draft[end:]
    draft = validate_plain_text(draft)
    if _substantive_text(draft) == _substantive_text(resume):
        raise ResumeProviderError(reason="no_effective_edits")
    summary = {"proposedCount": len(edits), "appliedCount": len(spans),
               "retainedCount": len(edits) - len(spans), "retainedReasonCounts": counts}
    return draft, summary


def validate_resume_review(raw: dict, *, resume: str, jd: str) -> tuple[dict, str]:
    try:
        result = ProviderResumeReview.model_validate(raw)
    except (ValidationError, TypeError, ValueError):
        raise ResumeProviderError(reason="review_schema_invalid") from None
    expected = {"completeness", "impact", "clarity", "structure"} | ({"roleMatch"} if jd else set())
    if len(result.dimensions) != len(expected) or {d.key for d in result.dimensions} != expected:
        raise ResumeProviderError(reason="dimension_set_invalid")
    texts = []
    for item in [*result.dimensions, *result.suggestions]:
        for evidence in item.evidence:
            source = resume if evidence.source == "resume" else jd
            if not source or evidence.quote not in source:
                raise ResumeProviderError(reason="evidence_quote_missing")
        if hasattr(item, "reason"):
            texts.append(item.reason)
            if item.key == "roleMatch" and {e.source for e in item.evidence} != {"resume", "jd"}:
                raise ResumeProviderError(reason="role_evidence_missing")
        else:
            texts.extend([item.title, item.explanation, item.recommendation])
    if any(not _chinese(t) for t in texts):
        raise ResumeProviderError(reason="explanation_language_invalid")
    if any(not t.strip() or len(t) > 600 or not _chinese(t) for t in result.missing_facts):
        raise ResumeProviderError(reason="missing_facts_language_invalid")
    draft, edit_summary = _safe_edit_draft(result.edits, resume=resume)
    review = {
        "overallScore": int(sum(d.score for d in result.dimensions) / len(result.dimensions) + .5),
        "roleMatchingAssessed": bool(jd),
        "dimensions": [d.model_dump(by_alias=True) for d in result.dimensions],
        "suggestions": [s.model_dump(by_alias=True) for s in result.suggestions],
        "missingFacts": result.missing_facts,
        "disclaimer": DISCLAIMER,
        "editSummary": edit_summary,
    }
    return review, draft


class _DuplicateJsonKey(ValueError):
    """No key or document value is retained in the exception."""


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey()
        result[key] = value
    return result


def _reject_json_constant(_value):
    # Python's decoder otherwise accepts NaN and Infinity, which are not JSON.
    raise ValueError()


def _finite_json_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError()
    return result


def _load_json_object(text, *, reason, ambiguous_reason=None):
    try:
        value = json.loads(text, object_pairs_hook=_unique_json_object,
                           parse_constant=_reject_json_constant, parse_float=_finite_json_float)
    except _DuplicateJsonKey:
        raise ResumeProviderError(reason=ambiguous_reason or reason) from None
    except (ValueError, TypeError, RecursionError):
        raise ResumeProviderError(reason=reason) from None
    if type(value) is not dict:
        raise ResumeProviderError(reason=reason)
    return value


def _parse_provider_content(content):
    """Unwrap only a whole json fence/BOM; never search for or repair JSON."""
    if type(content) is not str:
        raise ResumeProviderError(reason="provider_envelope_invalid")
    try:
        # Unpaired surrogates cannot be safely displayed or exported as UTF-8.
        content.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ResumeProviderError(reason="content_encoding_invalid") from None
    text = content.strip()
    if text.startswith("\ufeff"):
        text = text[1:].strip()
    if text.startswith("```"):
        fence = re.fullmatch(r"```json[ \t]*\r?\n([\s\S]*?)\r?\n```", text)
        if fence is None:
            raise ResumeProviderError(reason="content_json_invalid")
        text = fence.group(1)
    return _load_json_object(text, reason="content_json_invalid",
                             ambiguous_reason="content_json_ambiguous")


class CNResumeOptimizerProvider:
    def __init__(self, settings: Settings, *, transport=None):
        self.settings = settings
        self.transport = transport
        self.prompt = (REPO_ROOT / "ai/prompts/resume-optimizer/review.zh-CN.v2.md").read_text(encoding="utf-8")

    async def generate(self, *, resume: str, jd: str, target_role: str) -> tuple[dict, str]:
        if not self.settings.chat_qwen_api_key or not self.settings.chat_qwen_base_url:
            raise ResumeProviderError("provider_unconfigured", reason="provider_unconfigured")
        try:
            async with httpx.AsyncClient(transport=self.transport,
                    timeout=httpx.Timeout(90, connect=5), limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)) as client:
                # Stream the HTTP body only to bound bytes before JSON parsing.
                async with client.stream("POST", self.settings.chat_qwen_base_url.rstrip("/") + "/chat/completions",
                        headers={"Authorization": f"Bearer {self.settings.chat_qwen_api_key}"},
                        json={"model": self.settings.chat_qwen_model, "stream": False, "enable_thinking": False,
                              "max_tokens": 6500, "messages": [{"role": "system", "content": self.prompt},
                              {"role": "user", "content": json.dumps({"resume": resume, "jd": jd, "targetRole": target_role}, ensure_ascii=False)}]}) as response:
                    response.raise_for_status()
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 256 * 1024:
                            raise ResumeProviderError(reason="response_too_large")
                        chunks.append(chunk)
            try:
                body = b"".join(chunks).decode("utf-8", errors="strict")
            except UnicodeError:
                raise ResumeProviderError(reason="response_encoding_invalid") from None
            payload = _load_json_object(body, reason="provider_envelope_invalid")
            choice = payload["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ResumeProviderError(reason="provider_finish_length")
            if choice.get("finish_reason") != "stop":
                raise ResumeProviderError(reason="provider_finish_invalid")
            content = choice["message"]["content"]
            raw = _parse_provider_content(content)
            return validate_resume_review(raw, resume=resume, jd=jd)
        except ResumeProviderError:
            raise
        except httpx.TimeoutException:
            raise ResumeProviderError("provider_timeout", reason="provider_timeout") from None
        except httpx.HTTPError:
            raise ResumeProviderError("provider_unavailable", reason="provider_http_error") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise ResumeProviderError(reason="provider_envelope_invalid") from None
