from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limit import RateLimiter
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    Enable2FAResponse,
    Verify2FARequest,
    Disable2FARequest,
)
from app.services import auth as auth_service
from app.services import password_reset as password_reset_service
from app.services import email_verification as email_verification_service
from app.services import two_factor as two_factor_service
from app.services import oauth as oauth_service
from app.services import session_mgmt as session_service
from app.services.user import get_user_by_email
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=5, window_seconds=60)),
):
    return await auth_service.register(db, body.email, body.password)


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=10, window_seconds=60)),
):
    return await auth_service.login(db, body.email, body.password, totp_code=body.totp_code, backup_code=body.backup_code)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=10, window_seconds=60)),
):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.logout(db, token, body.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=3, window_seconds=300)),
):
    token = await password_reset_service.forgot_password(db, body.email)
    if settings.DEBUG:
        return {"message": "Password reset link sent", "reset_token": token}
    return {"message": "Password reset link sent if account exists"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await password_reset_service.reset_password(db, body.token, body.new_password)
    return {"message": "Password reset successful"}


@router.get("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    await email_verification_service.confirm_verification(token, db)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=3, window_seconds=300)),
):
    user = await get_user_by_email(db, body.email)
    if user and not user.is_verified:
        await email_verification_service.send_verification_email(db, user)
    return {"message": "Verification email sent if account exists"}


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await two_factor_service.enable_2fa(db, current_user)
    return result


@router.post("/2fa/verify")
async def verify_2fa(
    body: Verify2FARequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await two_factor_service.verify_2fa_setup(db, current_user, body.totp_code)
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    body: Disable2FARequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await two_factor_service.disable_2fa(db, current_user, body.password, body.totp_code, body.backup_code)
    return {"message": "2FA disabled successfully"}


@router.get("/oauth/google")
async def oauth_google():
    return {"url": oauth_service.google_auth_url()}


@router.get("/oauth/google/callback")
async def oauth_google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    return await oauth_service.oauth_login(db, "google", code)


@router.get("/oauth/github")
async def oauth_github():
    return {"url": oauth_service.github_auth_url()}


@router.get("/oauth/github/callback")
async def oauth_github_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    return await oauth_service.oauth_login(db, "github", code)


@router.get("/sessions")
async def list_sessions(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sid = decode_token(token).get("sid", "")
    sessions = await session_service.get_user_sessions(db, str(current_user.id), sid)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await session_service.revoke_session_by_id(db, session_id, str(current_user.id))
    return {"message": "Session revoked"}


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sid = decode_token(token).get("sid", "")
    await session_service.revoke_other_sessions(db, sid, str(current_user.id))
    return {"message": "Other sessions revoked"}