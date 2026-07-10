from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ports.authentication import AuthSessionStatus, IdentityProviderKind, WechatAuthorizationStatus


class RegisterUserRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    login_id: str = Field(min_length=3, alias="loginId")
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, alias="displayName")
    client_label: str = Field(default="web", alias="clientLabel")


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    login_id: str = Field(min_length=3, alias="loginId")
    password: str = Field(min_length=1)
    client_label: str = Field(default="web", alias="clientLabel")


class SmsSendCodeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    phone_number: str = Field(min_length=5, alias="phoneNumber")
    client_label: str = Field(default="web", alias="clientLabel")


class SmsSendCodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    challenge_id: str = Field(alias="challengeId")
    status: str
    provider: str
    expires_at_ms: int = Field(alias="expiresAtMs")
    cooldown_seconds: int = Field(alias="cooldownSeconds")
    masked_phone: str = Field(alias="maskedPhone")


class SmsVerifyLoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    phone_number: str = Field(min_length=5, alias="phoneNumber")
    challenge_id: str = Field(min_length=1, alias="challengeId")
    code: str = Field(min_length=4, max_length=8)
    client_label: str = Field(default="web", alias="clientLabel")


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    refresh_token: str = Field(min_length=1, alias="refreshToken")


class LogoutRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    logout_all_devices: bool = Field(default=False, alias="logoutAllDevices")


class SafeIdentityBindingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    binding_id: str = Field(alias="bindingId")
    provider: IdentityProviderKind
    display_name: str | None = Field(default=None, alias="displayName")
    status: str
    bound_at_ms: int = Field(alias="boundAtMs")


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(alias="userId")
    login_id: str = Field(alias="loginId")
    display_name: str = Field(alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    login_provider: IdentityProviderKind = Field(alias="loginProvider")
    created_at_ms: int = Field(alias="createdAtMs")
    last_login_at_ms: int = Field(alias="lastLoginAtMs")
    bindings: list[SafeIdentityBindingResponse] = Field(default_factory=list)
    membership_anchor_ref: str | None = Field(default=None, alias="membershipAnchorRef")


class AuthTokensResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_in_seconds: int = Field(alias="expiresInSeconds")


class AuthenticationResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user: CurrentUserResponse
    tokens: AuthTokensResponse
    auth_session_id: str = Field(alias="authSessionId")


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    auth_session_id: str = Field(alias="authSessionId")
    client_label: str = Field(alias="clientLabel")
    status: AuthSessionStatus
    issued_at_ms: int = Field(alias="issuedAtMs")
    expires_at_ms: int = Field(alias="expiresAtMs")
    last_used_at_ms: int = Field(alias="lastUsedAtMs")
    revoked_at_ms: int | None = Field(default=None, alias="revokedAtMs")


class AuthSessionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    sessions: list[AuthSessionResponse] = Field(default_factory=list)


class LogoutResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    revoked_session_ids: list[str] = Field(alias="revokedSessionIds")


class WechatAuthorizationSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    client_label: str = Field(default="web", alias="clientLabel")


class WechatAuthorizationSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    auth_request_id: str = Field(alias="authRequestId")
    provider: IdentityProviderKind
    status: WechatAuthorizationStatus
    authorization_url: str = Field(alias="authorizationUrl")
    qr_code_text: str = Field(alias="qrCodeText")
    expires_at_ms: int = Field(alias="expiresAtMs")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    provider_subject_hint: str = Field(alias="providerSubjectHint")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_account: bool | None = Field(default=None, alias="createdAccount")
    result: AuthenticationResultResponse | None = None


class WechatCallbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    state: str = Field(min_length=1)
    code: str = Field(min_length=1)


class WechatCompatibleActionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    auth_request_id: str = Field(alias="authRequestId")
