from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import admin_global_commerce
from app.core.config import Settings
from app.services.admin_service import AdminPrincipal
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService


class FakeAdminRepository:
    def __init__(self) -> None:
        self.results: dict[tuple[str, str, str], dict[str, object]] = {}

    def list_global_members(self, *, search: str, limit: int, offset: int):
        return [{"user_id": "global-user-1", "email": "candidate@example.com", "display_name": "Candidate"}]

    def global_member_identity(self, user_id: str):
        if user_id != "global-user-1":
            return None
        return {"user_id": user_id, "email": "candidate@example.com", "display_name": "Candidate", "created_at_ms": 1}

    def idempotent_result(self, *, actor_user_id: str, action: str, key: str):
        return self.results.get((actor_user_id, action, key))

    def save_idempotent_result(self, *, actor_user_id: str, action: str, key: str, result: dict[str, object]):
        self.results[(actor_user_id, action, key)] = result


class FakeAdminService:
    def __init__(self) -> None:
        self.repository = FakeAdminRepository()
        self.audits: list[dict[str, object]] = []

    def audit(self, **kwargs) -> None:
        self.audits.append(kwargs)


def principal() -> AdminPrincipal:
    return AdminPrincipal("admin-session", "admin-user", "super_admin", frozenset({"users.read", "payments.manage"}), 1)


def request():
    return SimpleNamespace(state=SimpleNamespace(request_context=SimpleNamespace(request_id="request-1")), client=None, headers={})


def test_global_member_search_detail_grant_and_targeted_revoke(monkeypatch) -> None:
    control = FakeAdminService()
    service = GlobalCommerceService(Settings(product_edition="global"), InMemoryGlobalCommerceRepository())
    monkeypatch.setattr(admin_global_commerce, "get_settings", lambda: Settings(product_edition="global"))
    monkeypatch.setattr(admin_global_commerce, "admin_service", lambda: control)

    listed = admin_global_commerce.list_members(principal(), search="candidate", limit=30, offset=0)
    assert listed["data"]["items"][0]["email"] == "candidate@example.com"

    payload = admin_global_commerce.MemberGrantRequest(
        offerCode="global-pro-weekly", idempotencyKey="member-grant-123", confirmed=True, reason="support grant"
    )
    first = admin_global_commerce.grant_member_plan("global-user-1", payload, request(), principal(), service)
    replay = admin_global_commerce.grant_member_plan("global-user-1", payload, request(), principal(), service)
    assert first == replay
    assert first["data"]["offerCode"] == "global-pro-weekly"
    assert first["data"]["endsAtMs"] - first["data"]["startsAtMs"] == 7 * 86_400_000
    assert len(service.repository.orders_for_user("global-user-1")) == 0

    detail = admin_global_commerce.member_detail("global-user-1", principal(), service)["data"]
    assert detail["identity"]["email"] == "candidate@example.com"
    assert detail["state"]["usage"]["copilotUnlimited"] is True

    entitlement_id = str(first["data"]["id"])
    revoke_payload = admin_global_commerce.MemberRevokeRequest(
        idempotencyKey="member-revoke-123", confirmed=True, reason="support revoke"
    )
    revoked = admin_global_commerce.revoke_member_entitlement(
        "global-user-1", entitlement_id, revoke_payload, request(), principal(), service
    )
    assert revoked["data"]["status"] == "revoked"
    assert service.repository.orders_for_user("global-user-1") == []
    assert len(control.audits) == 2


def test_global_member_workspace_is_hidden_in_chinese_edition(monkeypatch) -> None:
    monkeypatch.setattr(admin_global_commerce, "get_settings", lambda: Settings(product_edition="cn"))
    with pytest.raises(HTTPException) as error:
        admin_global_commerce.list_members(principal(), search="candidate", limit=30, offset=0)
    assert error.value.status_code == 404


def test_initial_free_entitlement_cannot_be_revoked_by_admin(monkeypatch) -> None:
    control = FakeAdminService()
    service = GlobalCommerceService(Settings(product_edition="global"), InMemoryGlobalCommerceRepository())
    free = service.ensure_free_grant("global-user-1", now_ms=1)
    monkeypatch.setattr(admin_global_commerce, "get_settings", lambda: Settings(product_edition="global"))
    monkeypatch.setattr(admin_global_commerce, "admin_service", lambda: control)
    payload = admin_global_commerce.MemberRevokeRequest(
        idempotencyKey="free-revoke-123", confirmed=True, reason="should fail"
    )
    with pytest.raises(HTTPException) as error:
        admin_global_commerce.revoke_member_entitlement(
            "global-user-1", free.entitlement_id, payload, request(), principal(), service
        )
    assert error.value.status_code == 422
