from __future__ import annotations

from pathlib import Path
import re

from app.ports.interview_session import InterviewLanguage, ProgrammingLanguage


_LANGUAGE_LABELS: dict[ProgrammingLanguage, tuple[str, str]] = {
    "python": ("Python", "python"),
    "java": ("Java", "java"),
    "cpp": ("C++", "cpp"),
    "javascript": ("JavaScript", "javascript"),
    "typescript": ("TypeScript", "typescript"),
    "go": ("Go", "go"),
}
_POLICY_PATTERN = re.compile(r"<programming_policy>.*?</programming_policy>", re.DOTALL)


def render_programming_policy(
    *, programming_required: bool, programming_language: ProgrammingLanguage | None,
    interview_language: InterviewLanguage
) -> str:
    if not programming_required:
        return ""
    language = programming_language or "python"
    language_label, fence_label = _LANGUAGE_LABELS[language]
    root = Path(__file__).resolve().parents[4] / "ai/prompts/programming-policy"
    filename = "policy.en.md" if interview_language == "en-US" else "policy.md"
    return (root / filename).read_text(encoding="utf-8").strip().format(
        language_label=language_label,
        fence_label=fence_label,
    )


def append_programming_policy(system_prompt: str, *, session: object) -> str:
    policy = render_programming_policy(
        programming_required=bool(getattr(session, "programming_required", False)),
        programming_language=getattr(session, "programming_language", None),
        interview_language=getattr(session, "interview_language", "zh-CN"),
    )
    return f"{system_prompt}\n\n{policy}" if policy else system_prompt


def carry_programming_policy(system_prompt: str, original_system_prompt: str) -> str:
    match = _POLICY_PATTERN.search(original_system_prompt)
    return f"{system_prompt}\n\n{match.group(0)}" if match else system_prompt
