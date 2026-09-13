from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from pathlib import Path
import re

InterviewLanguage = Literal[
    "zh-CN", "en-US", "ja-JP", "ko-KR", "vi-VN", "th-TH", "id-ID", "ms-MY", "fil-PH", "hi-IN",
    "ar-SA", "fr-FR", "de-DE", "es-ES", "pt-BR", "ru-RU", "it-IT", "nl-NL", "sv-SE", "da-DK",
    "fi-FI", "nb-NO", "el-GR", "pl-PL", "cs-CZ", "hu-HU", "ro-RO", "bg-BG", "hr-HR", "sk-SK",
]
InterviewLanguageTier = Literal["production", "beta"]

@dataclass(frozen=True)
class InterviewLanguageDefinition:
    locale: InterviewLanguage
    label: str
    native_label: str
    asr_language_code: str
    output_language: str
    tier: InterviewLanguageTier
    direction: Literal["ltr", "rtl"] = "ltr"


_PRODUCTION = {"zh-CN", "en-US", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES", "pt-BR", "it-IT", "ru-RU"}
_LABELS: dict[InterviewLanguage, tuple[str, str, str, str]] = {
    "zh-CN": ("Chinese", "中文", "zh", "Chinese"), "en-US": ("English", "English", "en", "English"),
    "ja-JP": ("Japanese", "日本語", "ja", "Japanese"), "ko-KR": ("Korean", "한국어", "ko", "Korean"),
    "vi-VN": ("Vietnamese", "Tiếng Việt", "vi", "Vietnamese"), "th-TH": ("Thai", "ไทย", "th", "Thai"),
    "id-ID": ("Indonesian", "Bahasa Indonesia", "id", "Indonesian"), "ms-MY": ("Malay", "Bahasa Melayu", "ms", "Malay"),
    "fil-PH": ("Filipino", "Filipino", "fil", "Filipino"), "hi-IN": ("Hindi", "हिन्दी", "hi", "Hindi"),
    "ar-SA": ("Arabic", "العربية", "ar", "Arabic"), "fr-FR": ("French", "Français", "fr", "French"),
    "de-DE": ("German", "Deutsch", "de", "German"), "es-ES": ("Spanish", "Español", "es", "Spanish"),
    "pt-BR": ("Portuguese", "Português", "pt", "Portuguese"), "ru-RU": ("Russian", "Русский", "ru", "Russian"),
    "it-IT": ("Italian", "Italiano", "it", "Italian"), "nl-NL": ("Dutch", "Nederlands", "nl", "Dutch"),
    "sv-SE": ("Swedish", "Svenska", "sv", "Swedish"), "da-DK": ("Danish", "Dansk", "da", "Danish"),
    "fi-FI": ("Finnish", "Suomi", "fi", "Finnish"), "nb-NO": ("Norwegian", "Norsk", "no", "Norwegian"),
    "el-GR": ("Greek", "Ελληνικά", "el", "Greek"), "pl-PL": ("Polish", "Polski", "pl", "Polish"),
    "cs-CZ": ("Czech", "Čeština", "cs", "Czech"), "hu-HU": ("Hungarian", "Magyar", "hu", "Hungarian"),
    "ro-RO": ("Romanian", "Română", "ro", "Romanian"), "bg-BG": ("Bulgarian", "Български", "bg", "Bulgarian"),
    "hr-HR": ("Croatian", "Hrvatski", "hr", "Croatian"), "sk-SK": ("Slovak", "Slovenčina", "sk", "Slovak"),
}

INTERVIEW_LANGUAGE_REGISTRY: dict[InterviewLanguage, InterviewLanguageDefinition] = {
    locale: InterviewLanguageDefinition(locale, label, native, code, output, "production" if locale in _PRODUCTION else "beta", "rtl" if locale == "ar-SA" else "ltr")
    for locale, (label, native, code, output) in _LABELS.items()
}

DEFAULT_GLOBAL_INTERVIEW_LANGUAGE: InterviewLanguage = "en-US"

_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_HANGUL = re.compile(r"[\uac00-\ud7af]")
_KANA = re.compile(r"[\u3040-\u30ff]")
_ARABIC = re.compile(r"[\u0600-\u06ff]")
_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_GREEK = re.compile(r"[\u0370-\u03ff]")
_LATIN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]" )


def interview_prompt_directory(locale: str, *, repository_root: Path | None = None) -> Path:
    """Return the checked-in prompt directory for a registered locale."""
    root = repository_root or Path(__file__).resolve().parents[4]
    return root / "ai" / "prompts" / "global-interview" / locale


def interview_prompt_assets_ready(locale: str, *, repository_root: Path | None = None) -> bool:
    definition = get_interview_language(locale)
    if definition is None:
        return False
    directory = interview_prompt_directory(locale, repository_root=repository_root)
    return all((directory / f"{stage}.md").is_file() for stage in ("system", "quick", "detail", "continuation", "screenshot"))


def output_language_violation(value: str, locale: str) -> bool:
    """Conservative script guard; allows product names, code and source evidence."""
    text = value.strip()
    if not text:
        return True
    counts = {
        "han": len(_HAN.findall(text)),
        "hangul": len(_HANGUL.findall(text)),
        "kana": len(_KANA.findall(text)),
        "arabic": len(_ARABIC.findall(text)),
        "cyrillic": len(_CYRILLIC.findall(text)),
        "greek": len(_GREEK.findall(text)),
        "latin": len(_LATIN.findall(text)),
    }
    # Chinese/Japanese/Korean/Arabic/Russian/Greek have distinctive scripts.
    if locale == "zh-CN":
        return counts["han"] < 2 and len(text) > 40
    if locale == "ja-JP":
        return counts["kana"] < 2 and counts["han"] < 2 and len(text) > 40
    if locale == "ko-KR":
        return counts["hangul"] < 2 and len(text) > 40
    if locale == "ar-SA":
        return counts["arabic"] < 2 and len(text) > 40
    if locale == "ru-RU":
        return counts["cyrillic"] < 2 and len(text) > 40
    if locale == "el-GR":
        return counts["greek"] < 2 and len(text) > 40
    # Latin locales must not silently publish Chinese, Cyrillic, Arabic or Greek prose.
    if locale in INTERVIEW_LANGUAGE_REGISTRY and locale not in {"zh-CN", "ja-JP", "ko-KR", "ar-SA", "ru-RU", "el-GR"}:
        dominant = max(counts["han"], counts["cyrillic"], counts["arabic"], counts["greek"])
        return dominant >= 4 and dominant / max(1, sum(counts.values())) >= 0.08
    return False


def get_interview_language(locale: str) -> InterviewLanguageDefinition | None:
    return INTERVIEW_LANGUAGE_REGISTRY.get(locale)  # type: ignore[arg-type]


def is_production_interview_language(locale: str) -> bool:
    definition = get_interview_language(locale)
    return bool(definition and definition.tier == "production")


def asr_language_code(locale: str) -> str:
    definition = get_interview_language(locale)
    return definition.asr_language_code if definition else "en"
