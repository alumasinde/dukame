import os

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import ForgotPasswordRequest, LoginRequest, MessageResponse, RefreshRequest, RegisterRequest, ResendVerificationRequest, ResetPasswordRequest, TokenResponse, UserResponse, VerifyEmailRequest
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import create_access_token, decode_access_token, get_current_user
from app.models.identity import AuthSession, User
from app.services.auth import authenticate, logout, register_user, rotate_refresh_token
from app.services.identity_tokens import issue_password_reset_token, issue_verification_token, reset_password, verify_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User, session: AuthSession, refresh: str) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user, session), refresh_token=refresh, expires_in=settings.access_token_ttl_seconds)


def _frontend_url(path: str, token: str) -> str:
    base = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/{path}?token={token}"


async def _send_auth_email(to: str, subject: str, body: str) -> None:
    try:
        await send_email(to, subject, body)
    except RuntimeError:
        if settings.is_production:
            raise


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    user = await register_user(db, payload.email, payload.password, payload.first_name, payload.last_name, payload.phone)
    token = await issue_verification_token(db, user)
    await db.commit()
    await _send_auth_email(user.email, "Verify your DukaMe account", f"Verify your account: {_frontend_url('verify-email', token)}")
    await db.refresh(user)
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/verify-email", response_model=MessageResponse)
async def verify(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await verify_email(db, payload.token)
    await db.commit()
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.strip().lower(), User.is_active.is_(True), User.is_verified.is_(False)))
    if user:
        token = await issue_verification_token(db, user)
        await db.commit()
        await _send_auth_email(user.email, "Verify your DukaMe account", f"Verify your account: {_frontend_url('verify-email', token)}")
    return MessageResponse(message="If the account exists and needs verification, a verification message has been sent")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.strip().lower(), User.is_active.is_(True)))
    if user:
        token = await issue_password_reset_token(db, user)
        await db.commit()
        await _send_auth_email(user.email, "Reset your DukaMe password", f"Reset your password: {_frontend_url('reset-password', token)}")
    return MessageResponse(message="If the account exists, a password reset message has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await reset_password(db, payload.token, payload.password)
    await db.commit()
    return MessageResponse(message="Password reset successfully")


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user, session, refresh = await authenticate(db, payload.email, payload.password, request.headers.get("user-agent"), request.client.host if request.client else None)
    await db.commit()
    return _token_response(user, session, refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user, session, refresh_token = await rotate_refresh_token(db, payload.refresh_token, request.headers.get("user-agent"), request.client.host if request.client else None)
    await db.commit()
    return _token_response(user, session, refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_current(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    authorization = request.headers.get("authorization", "")
    token = authorization.split(" ", 1)[1] if " " in authorization else ""
    payload = decode_access_token(token)
    await logout(db, str(payload["sid"]), user.id)
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)
