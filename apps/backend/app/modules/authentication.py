from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import authentication_service, require_authenticated_context
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.authentication import (
    AuthSessionListResponse,
    AuthSessionResponse,
    AuthenticationResultResponse,
    AuthTokensResponse,
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterUserRequest,
    SafeIdentityBindingResponse,
    WechatAuthorizationSessionRequest,
    WechatAuthorizationSessionResponse,
    WechatCallbackRequest,
    SmsSendCodeRequest,
    SmsSendCodeResponse,
    SmsVerifyLoginRequest,
)
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.authentication_service import AuthenticationService


router = APIRouter(prefix="/auth", tags=["authentication"])
descriptor = ModuleDescriptor(
    feature="authentication",
    owningApp="apps/backend",
    routePrefix="/api/v1/auth",
    mode="active",
    notes="Unified account registration, login, JWT access-token, refresh-session, and authenticated-user boundaries.",
)


def _to_user_response(user) -> CurrentUserResponse:
    return CurrentUserResponse(
        userId=user.user_id,
        loginId=user.login_id,
        displayName=user.display_name,
        avatarUrl=user.avatar_url,
        loginProvider=user.last_login_provider,
        createdAtMs=user.created_at_ms,
        lastLoginAtMs=user.last_login_at_ms,
        bindings=[
            SafeIdentityBindingResponse(
                bindingId=item.binding_id,
                provider=item.provider,
                displayName=item.display_name,
                status=item.status,
                boundAtMs=item.bound_at_ms,
            )
            for item in user.bindings
        ],
        membershipAnchorRef=user.membership_anchor_ref,
    )


def _to_wechat_session_response(session, service: AuthenticationService) -> WechatAuthorizationSessionResponse:
    result = None
    created_account = None
    if session.resolved_user_id and session.auth_session_id and session.access_token and session.refresh_token:
        user = service.get_current_user(auth_context=AuthenticatedRequestContext(user_id=session.resolved_user_id, login_id=f"wechat:{session.provider_subject_hint}", auth_session_id=session.auth_session_id))
        auth_session = service.repository.get_auth_session(session.auth_session_id)
        if auth_session is not None:
            result = _to_result_response(user, auth_session, session.access_token, session.refresh_token, service)
            created_account = len([binding for binding in user.bindings if binding.provider == "wechat"]) == 1 and user.created_at_ms == user.last_login_at_ms
    return WechatAuthorizationSessionResponse(
        authRequestId=session.auth_request_id,
        provider=session.provider,
        status=session.status,
        authorizationUrl=session.authorization_url,
        qrCodeText=session.qr_code_text,
        expiresAtMs=session.expires_at_ms,
        createdAtMs=session.created_at_ms,
        updatedAtMs=session.updated_at_ms,
        providerSubjectHint=session.provider_subject_hint,
        errorCode=session.error_code,
        errorMessage=session.error_message,
        createdAccount=created_account,
        result=result,
    )


def _to_result_response(user, auth_session, access_token: str, refresh_token: str, service: AuthenticationService) -> AuthenticationResultResponse:
    return AuthenticationResultResponse(
        user=_to_user_response(user),
        tokens=AuthTokensResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="Bearer",
            expiresInSeconds=service.settings.auth_access_token_ttl_seconds,
        ),
        authSessionId=auth_session.auth_session_id,
    )


def _mask_phone(phone_e164: str) -> str:
    digits = phone_e164.removeprefix("+86")
    return f"{digits[:3]}****{digits[-4:]}" if len(digits) == 11 else "已验证手机号"


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "authentication", "message": "Authentication Service is available for account, token, and session management."},
        timestamp=utc_now_iso(),
    )


@router.post("/register", response_model=ApiEnvelope[AuthenticationResultResponse])
async def register(
    request_context: Request,
    request: RegisterUserRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[AuthenticationResultResponse]:
    user, auth_session, access_token, refresh_token = service.register_user(
        login_id=request.login_id,
        password=request.password,
        display_name=request.display_name,
        client_label=request.client_label,
    )
    return success_response(request=request_context, data=_to_result_response(user, auth_session, access_token, refresh_token, service), timestamp=utc_now_iso())


@router.post("/login", response_model=ApiEnvelope[AuthenticationResultResponse])
async def login(
    request_context: Request,
    request: LoginRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[AuthenticationResultResponse]:
    user, auth_session, access_token, refresh_token = service.login(
        login_id=request.login_id,
        password=request.password,
        client_label=request.client_label,
    )
    return success_response(request=request_context, data=_to_result_response(user, auth_session, access_token, refresh_token, service), timestamp=utc_now_iso())


@router.post("/sms/send-code", response_model=ApiEnvelope[SmsSendCodeResponse])
async def send_sms_code(
    request_context: Request,
    request: SmsSendCodeRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[SmsSendCodeResponse]:
    challenge = service.send_sms_code(phone_number=request.phone_number, client_label=request.client_label)
    return success_response(
        request=request_context,
        data=SmsSendCodeResponse(
            challengeId=challenge.challenge_id,
            status=challenge.status,
            provider=challenge.provider,
            expiresAtMs=challenge.expires_at_ms,
            cooldownSeconds=service.settings.auth_sms_send_interval_seconds,
            maskedPhone=_mask_phone(challenge.phone_e164),
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/sms/verify-login", response_model=ApiEnvelope[AuthenticationResultResponse])
async def verify_sms_login(
    request_context: Request,
    request: SmsVerifyLoginRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[AuthenticationResultResponse]:
    user, auth_session, access_token, refresh_token = service.verify_sms_login(
        challenge_id=request.challenge_id,
        phone_number=request.phone_number,
        code=request.code,
        client_label=request.client_label,
    )
    return success_response(request=request_context, data=_to_result_response(user, auth_session, access_token, refresh_token, service), timestamp=utc_now_iso())


@router.post("/refresh", response_model=ApiEnvelope[AuthenticationResultResponse])
async def refresh(
    request_context: Request,
    request: RefreshTokenRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[AuthenticationResultResponse]:
    user, auth_session, access_token, refresh_token = service.refresh(refresh_token=request.refresh_token)
    return success_response(request=request_context, data=_to_result_response(user, auth_session, access_token, refresh_token, service), timestamp=utc_now_iso())


@router.get("/me", response_model=ApiEnvelope[CurrentUserResponse])
async def me(
    request: Request,
    auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context),
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[CurrentUserResponse]:
    user = service.get_current_user(auth_context=auth_context)
    return success_response(request=request, data=_to_user_response(user), timestamp=utc_now_iso())


@router.get("/sessions", response_model=ApiEnvelope[AuthSessionListResponse])
async def sessions(
    request: Request,
    auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context),
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[AuthSessionListResponse]:
    sessions = service.list_auth_sessions(auth_context=auth_context)
    return success_response(
        request=request,
        data=AuthSessionListResponse(
            sessions=[
                AuthSessionResponse(
                    authSessionId=item.auth_session_id,
                    clientLabel=item.client_label,
                    status=item.status,
                    issuedAtMs=item.issued_at_ms,
                    expiresAtMs=item.expires_at_ms,
                    lastUsedAtMs=item.last_used_at_ms,
                    revokedAtMs=item.revoked_at_ms,
                )
                for item in sessions
            ]
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/logout", response_model=ApiEnvelope[LogoutResponse])
async def logout(
    request_context: Request,
    request: LogoutRequest,
    auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context),
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[LogoutResponse]:
    revoked = service.logout(auth_context=auth_context, logout_all_devices=request.logout_all_devices)
    return success_response(request=request_context, data=LogoutResponse(revokedSessionIds=revoked), timestamp=utc_now_iso())


@router.post("/wechat/authorization-sessions", response_model=ApiEnvelope[WechatAuthorizationSessionResponse])
async def create_wechat_authorization_session(
    request_context: Request,
    request: WechatAuthorizationSessionRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[WechatAuthorizationSessionResponse]:
    session = service.create_wechat_authorization_session(client_label=request.client_label)
    return success_response(request=request_context, data=_to_wechat_session_response(session, service), timestamp=utc_now_iso())


@router.get("/wechat/authorization-sessions/{auth_request_id}", response_model=ApiEnvelope[WechatAuthorizationSessionResponse])
async def get_wechat_authorization_session(
    auth_request_id: str,
    request: Request,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[WechatAuthorizationSessionResponse]:
    session = service.get_wechat_authorization_session(auth_request_id=auth_request_id)
    return success_response(request=request, data=_to_wechat_session_response(session, service), timestamp=utc_now_iso())


@router.post("/wechat/authorization-sessions/{auth_request_id}/scan", response_model=ApiEnvelope[WechatAuthorizationSessionResponse])
async def simulate_wechat_scan(
    auth_request_id: str,
    request: Request,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[WechatAuthorizationSessionResponse]:
    session = service.simulate_wechat_scan(auth_request_id=auth_request_id)
    return success_response(request=request, data=_to_wechat_session_response(session, service), timestamp=utc_now_iso())


@router.post("/wechat/authorization-sessions/{auth_request_id}/authorize", response_model=ApiEnvelope[WechatAuthorizationSessionResponse])
async def simulate_wechat_authorize(
    auth_request_id: str,
    request: Request,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[WechatAuthorizationSessionResponse]:
    session = service.simulate_wechat_authorize(auth_request_id=auth_request_id)
    return success_response(request=request, data=_to_wechat_session_response(session, service), timestamp=utc_now_iso())


@router.post("/wechat/callback", response_model=ApiEnvelope[WechatAuthorizationSessionResponse])
async def wechat_callback(
    request_context: Request,
    request: WechatCallbackRequest,
    service: AuthenticationService = Depends(authentication_service),
) -> ApiEnvelope[WechatAuthorizationSessionResponse]:
    session = service.complete_wechat_callback(state_token=request.state, code=request.code)
    return success_response(request=request_context, data=_to_wechat_session_response(session, service), timestamp=utc_now_iso())
