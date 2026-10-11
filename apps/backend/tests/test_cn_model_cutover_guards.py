"""Pure release guard tests: no SSH, Docker, credentials or production calls."""
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "cn_model_cutover", Path(__file__).resolve().parents[3] / "scripts/cutover_cn_shared_text_model.py"
)
cutover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cutover)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n", b""])
def test_replacement_changes_only_one_model_line(newline):
    before = b"UNRELATED_SETTING=unchanged\nOFFERSTEADY_CHAT_QWEN_MODEL=deepseek-v4-flash" + newline
    after = cutover.replacement(before)
    assert after == before.replace(b"deepseek-v4-flash", b"deepseek-v4.1-flash")


@pytest.mark.parametrize("data", [
    b"UNRELATED_SETTING=unchanged\n",
    b"OFFERSTEADY_CHAT_QWEN_MODEL=unknown-model\n",
    b"OFFERSTEADY_CHAT_QWEN_MODEL=deepseek-v4-flash\nOFFERSTEADY_CHAT_QWEN_MODEL=deepseek-v4-flash\n",
])
def test_unreviewed_environment_is_rejected(data):
    with pytest.raises(AssertionError):
        cutover.replacement(data)


def test_non_text_fields_are_all_in_invariant_check():
    assert {"mock_interview_tts_model", "screenshot_vision_model", "realtime_asr_model",
            "embedding_model", "rerank_model"} <= set(cutover.MODEL_FIELDS)


def test_atomic_write_preserves_permissions_and_rejects_leftover(tmp_path):
    target = tmp_path / "synthetic.env"
    target.write_bytes(b"original")
    target.chmod(0o600)
    cutover.atomic_write(target, b"replacement")
    assert target.read_bytes() == b"replacement"
    assert target.stat().st_mode & 0o777 == 0o600
    target.with_name(target.name + ".model-cutover.tmp").write_bytes(b"unrelated")
    with pytest.raises(FileExistsError):
        cutover.atomic_write(target, b"must-not-overwrite")
    assert target.read_bytes() == b"replacement"
