from app.core.config import Settings


def test_admin_session_defaults_cover_a_workday_without_expanding_step_up_window(monkeypatch) -> None:
    monkeypatch.delenv("OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS", raising=False)
    monkeypatch.delenv("OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS", raising=False)
    settings = Settings(_env_file=None)

    assert settings.admin_session_ttl_seconds == 8 * 60 * 60
    assert settings.admin_recent_mfa_ttl_seconds == 5 * 60


def test_admin_session_windows_remain_environment_configurable(monkeypatch) -> None:
    monkeypatch.setenv("OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS", "3600")
    monkeypatch.setenv("OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS", "120")

    settings = Settings(_env_file=None)

    assert settings.admin_session_ttl_seconds == 3600
    assert settings.admin_recent_mfa_ttl_seconds == 120
