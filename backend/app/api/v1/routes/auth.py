from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, get_current_user
from app.models.identity import AuthSession, User
from app.services.auth import authenticate, logout, register_user, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User, session: AuthSession, refresh: str) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user, session), refresh_token=refresh, expires_in=settings.access_token_ttl_seconds)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    user = await register_user(db, payload.email, payload.password, payload.first_name, payload.last_name, payload.phone)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user, from_attributes=True)


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


@router.post("/logout", status_code=204)
async def logout_current(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    authorization = request.headers.get("authorization", "")
    token = authorization.split(" ", 1)[1] if " " in authorization else ""
    payload = decode_access_token(token)
    await logout(db, str(payload["sid"]), user.id)
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)
