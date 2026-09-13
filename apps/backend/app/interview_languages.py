from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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


def get_interview_language(locale: str) -> InterviewLanguageDefinition | None:
    return INTERVIEW_LANGUAGE_REGISTRY.get(locale)  # type: ignore[arg-type]


def is_production_interview_language(locale: str) -> bool:
    definition = get_interview_language(locale)
    return bool(definition and definition.tier == "production")


def asr_language_code(locale: str) -> str:
    definition = get_interview_language(locale)
    return definition.asr_language_code if definition else "en"
