"""Pure fixed-scope release checks: never contact SSH, Docker or a provider."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def release(monkeypatch):
    directory = Path(__file__).resolve().parents[3] / "scripts"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("mock_tts_release", directory / "release_cn_mock_tts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_only_three_tts_settings_are_replaced(release, newline):
    before = b"UNRELATED=synthetic\n" + newline.join((k + "=" + v[0]).encode() for k, v in release.CHANGES.items()) + newline
    after = release.replacement(before)
    expected = before
    for key, (old, new) in release.CHANGES.items():
        expected = expected.replace((key + "=" + old).encode(), (key + "=" + new).encode())
    assert after == expected
    assert set(release.CHANGES) == {"OFFERSTEADY_MOCK_INTERVIEW_TTS_MODEL", "OFFERSTEADY_MOCK_INTERVIEW_TTS_VOICE", "OFFERSTEADY_MOCK_INTERVIEW_TTS_WS_URL"}


def test_implicit_defaults_become_only_three_explicit_settings(release):
    before = b"UNRELATED=synthetic"
    after = release.replacement(before)
    assert after == before + b"\n" + b"".join((k+"="+v[1]+"\n").encode() for k, v in release.CHANGES.items())


def test_duplicate_and_drifted_config_fail_closed(release):
    lines = [(k + "=" + v[0]).encode() for k, v in release.CHANGES.items()]
    for values in (lines + lines[:1], [lines[0] + b"unexpected"] + lines[1:]):
        with pytest.raises(AssertionError):
            release.replacement(b"\n".join(values) + b"\n")


def test_new_protocol_patch_preserves_known_cn_legacy_baseline(release):
    repo = Path(__file__).resolve().parents[3]
    source = (repo / "apps/backend/app/services/mock_interview_tts.py").read_text()
    cn = release.cn_source(source)
    assert "global_mock_interview_tts_ws_url" not in cn and "mock-interview/en/tts.txt" not in cn
    assert "async def _stream_audio_plus" in cn and "input_text_buffer.commit" in cn
    with pytest.raises(AssertionError):
        release.cn_source(cn)


def test_invariant_rejects_unrelated_runtime_changes(release):
    from copy import deepcopy
    before = {"Config": {"Env": ["UNRELATED=synthetic"] + [k+"="+v[0] for k, v in release.CHANGES.items()]}, "HostConfig": {}, "Mounts": []}
    after = deepcopy(before)
    after["Config"]["Env"] = ["UNRELATED=synthetic"] + [k+"="+v[1] for k, v in release.CHANGES.items()]
    after["Image"] = "synthetic-candidate"
    target = {"newImage": after["Image"]}
    release.invariant(before, after, target)
    changed = deepcopy(after)
    changed["Config"]["Env"].append("OFFERSTEADY_CHAT_QWEN_MODEL=unexpected")
    with pytest.raises(AssertionError):
        release.invariant(before, changed, target)
    changed = deepcopy(after)
    changed["HostConfig"]["PortBindings"] = {"8000": []}
    with pytest.raises(AssertionError):
        release.invariant(before, changed, target)


def test_two_idle_checks_precede_production_mutation(release):
    import inspect
    source = inspect.getsource(release.deploy)
    assert source.count("guards.idle_gate()") == 2
    assert source.rfind("guards.idle_gate()") < source.index("guards.atomic_write(")
    assert 'target["service"] == "backend"' in source
    assert "guards.verify_non_targets(manifest)" in source
