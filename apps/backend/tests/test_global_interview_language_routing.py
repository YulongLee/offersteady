from pathlib import Path

from app.interview_languages import INTERVIEW_LANGUAGE_REGISTRY, asr_language_code, get_interview_language
from app.services.chat_service import FilePromptTemplateAdapter
from app.core.config import Settings


def test_global_registry_exposes_production_languages_and_asr_codes() -> None:
    assert len(INTERVIEW_LANGUAGE_REGISTRY) == 30
    assert get_interview_language("ja-JP").output_language == "Japanese"
    assert asr_language_code("ko-KR") == "ko"
    assert get_interview_language("unknown") is None


def test_production_prompt_assets_exist_for_each_stage() -> None:
    root = Path(__file__).resolve().parents[3] / "ai" / "prompts" / "global-interview"
    for locale in ("zh-CN", "en-US", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES", "pt-BR", "it-IT", "ru-RU"):
        # Locale-specific resources are required for every production route.
        for stage in ("system", "quick", "detail", "continuation", "screenshot"):
            assert (root / locale / f"{stage}.md").exists()


def test_non_english_prompt_route_adds_output_language_contract() -> None:
    adapter = FilePromptTemplateAdapter(Settings())
    system_prompt, config = adapter.load_system_prompt("ja-JP")
    assert config.template_id == "interview-chat-ja-JP-system"
    assert "Japanese only" in system_prompt
