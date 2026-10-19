"""Isolated, bounded resume provider and conservative evidence validation."""
from __future__ import annotations

from collections import Counter
import json
import re

import httpx
from pydantic import ValidationError

from app.core.config import REPO_ROOT, Settings
from app.schemas.resume_optimizer import ProviderResumeReview

PROMPT_VERSION = "resume-optimizer-en-v1"
SCORE_VERSION = "resume-reference-v1"
DISCLAIMER = "Reference evaluation under OfferSteady's resume rubric, not a hiring probability. Verify all facts before use."


class ResumeProviderError(Exception):
    """Only a fixed category, never a provider response or document excerpt."""
    def __init__(self, category="invalid_output"):
        self.category = category if category in {"invalid_output", "provider_timeout", "provider_unavailable", "provider_unconfigured", "interrupted", "source_unavailable"} else "invalid_output"
        super().__init__(self.category)


def validate_plain_text(text: str) -> str:
    value = text.strip()
    if (not value or len(value) > 60000
            or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value)
            or re.search(r"</?[A-Za-z][^>]*>", value)):
        raise ResumeProviderError()
    return value


def _english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    latin = sum(c.isascii() for c in letters)
    return bool(letters) and latin / len(letters) >= .8 and bool(re.search(r"[A-Za-z]{2,}", text))


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
_NUMBERS = re.compile(r"(?<!\w)\d+(?:[.,:/-]\d+)*(?:\s?%)?")
_CONTACT = re.compile(r"https?://[^\s)]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)\+?\d[\d ()-]{6,}\d(?!\d)")
_LIMITED_AGENCY = re.compile(r"\b(helped|assisted|supported|contributed|participated)\b", re.I)
_STRONG_AGENCY = re.compile(r"\b(led|lead|owned|spearheaded|directed|architected|managed|designed|improved|ensured|enabled|expert|senior|principal|certified)\b", re.I)


def validate_resume_review(raw: dict, *, resume: str, jd: str) -> tuple[dict, str]:
    try:
        result = ProviderResumeReview.model_validate(raw)
    except (ValidationError, TypeError, ValueError):
        raise ResumeProviderError() from None
    expected = {"completeness", "impact", "clarity", "structure"} | ({"roleMatch"} if jd else set())
    if len(result.dimensions) != len(expected) or {d.key for d in result.dimensions} != expected:
        raise ResumeProviderError()
    texts = []
    for item in [*result.dimensions, *result.suggestions]:
        for evidence in item.evidence:
            source = resume if evidence.source == "resume" else jd
            if not source or evidence.quote not in source:
                raise ResumeProviderError()
        if hasattr(item, "reason"):
            texts.append(item.reason)
            if item.key == "roleMatch" and {e.source for e in item.evidence} != {"resume", "jd"}:
                raise ResumeProviderError()
        else:
            texts.extend([item.title, item.explanation, item.recommendation])
    if any(not _english(t) for t in texts):
        raise ResumeProviderError()
    if any(not t.strip() or len(t) > 600 or not _english(t) for t in result.missing_facts):
        raise ResumeProviderError()
    spans = []
    for edit in result.edits:
        quote, replacement = edit.source_quote, edit.replacement
        if resume.count(quote) != 1:
            raise ResumeProviderError()
        if Counter(_NUMBERS.findall(quote)) != Counter(_NUMBERS.findall(replacement)):
            raise ResumeProviderError()
        if Counter(_CONTACT.findall(quote)) != Counter(_CONTACT.findall(replacement)):
            raise ResumeProviderError()
        quote_words = Counter(w.rstrip(".-").lower() for w in _WORDS.findall(quote))
        replacement_words = Counter(w.rstrip(".-").lower() for w in _WORDS.findall(replacement))
        if any(word not in quote_words and word not in _SAFE_WORDS for word in replacement_words):
            raise ResumeProviderError()
        # Keep content-bearing nouns, negations and qualifiers in each edited
        # span; facts from a different role must not migrate into this one.
        if any(replacement_words[word] < count for word,count in quote_words.items() if word not in _SAFE_WORDS):
            raise ResumeProviderError()
        non_latin = lambda text: Counter(re.findall(r"[^\W\d_a-zA-Z]+", text, flags=re.UNICODE))
        if non_latin(quote) != non_latin(replacement):
            raise ResumeProviderError()
        # Do not upgrade collaborative responsibility into ownership/leadership.
        if _LIMITED_AGENCY.search(quote) and not _LIMITED_AGENCY.search(replacement):
            raise ResumeProviderError()
        if any(word.lower() not in quote.lower() for word in _STRONG_AGENCY.findall(replacement)):
            raise ResumeProviderError()
        start = resume.index(quote)
        end = start + len(quote)
        if any(start < other_end and end > other_start for other_start, other_end, _ in spans):
            raise ResumeProviderError()
        spans.append((start, end, replacement))
    draft = resume
    for start, end, replacement in sorted(spans, reverse=True):
        draft = draft[:start] + replacement + draft[end:]
    draft = validate_plain_text(draft)
    review = {
        "overallScore": int(sum(d.score for d in result.dimensions) / len(result.dimensions) + .5),
        "roleMatchingAssessed": bool(jd),
        "dimensions": [d.model_dump(by_alias=True) for d in result.dimensions],
        "suggestions": [s.model_dump(by_alias=True) for s in result.suggestions],
        "missingFacts": result.missing_facts,
        "disclaimer": DISCLAIMER,
    }
    return review, draft


class ResumeOptimizerProvider:
    def __init__(self, settings: Settings, *, transport=None):
        self.settings = settings
        self.transport = transport
        self.prompt = (REPO_ROOT / "ai/prompts/resume-optimizer/review.en.v1.md").read_text(encoding="utf-8")

    async def generate(self, *, resume: str, jd: str, target_role: str) -> tuple[dict, str]:
        if not self.settings.chat_qwen_api_key or not self.settings.chat_qwen_base_url:
            raise ResumeProviderError("provider_unconfigured")
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
                            raise ResumeProviderError()
                        chunks.append(chunk)
            payload = json.loads(b"".join(chunks))
            choice = payload["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ResumeProviderError()
            content = choice["message"]["content"]
            raw = json.loads(content)
            return validate_resume_review(raw, resume=resume, jd=jd)
        except ResumeProviderError:
            raise
        except httpx.TimeoutException:
            raise ResumeProviderError("provider_timeout") from None
        except httpx.HTTPError:
            raise ResumeProviderError("provider_unavailable") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise ResumeProviderError() from None
