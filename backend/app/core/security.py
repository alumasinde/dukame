from datetime import datetime, timedelta, UTC
import hashlib
import secrets
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.identity import AuthSession, User

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user: User, session: AuthSession) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.access_token_ttl_seconds)
    payload = {"sub": user.public_id, "sid": session.public_id, "typ": "access", "iat": now, "exp": expires, "iss": settings.app_name}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(settings.refresh_token_bytes)


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm], issuer=settings.app_name, options={"require": ["sub", "sid", "typ", "iat", "exp", "iss"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return payload


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    public_id, session_id = payload.get("sub"), payload.get("sid")
    if not isinstance(public_id, str) or not isinstance(session_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    result = await db.execute(select(User).join(AuthSession).where(User.public_id == public_id, AuthSession.public_id == session_id, AuthSession.revoked_at.is_(None), AuthSession.expires_at > datetime.now(UTC), User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")
    return user


def make_session(user: User, user_agent: str | None, ip_address: str | None) -> tuple[AuthSession, str]:
    refresh = new_refresh_token()
    session = AuthSession(public_id=uuid.uuid4().hex, user_id=user.id, refresh_token_hash=token_hash(refresh), expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds), user_agent=user_agent[:512] if user_agent else None, ip_address=ip_address)
    return session, refresh


def revoke_session(session: AuthSession) -> None:
    session.revoked_at = datetime.now(UTC)


async def revoke_all_user_sessions(db: AsyncSession, user_id: int) -> None:
    await db.execute(update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)).values(revoked_at=datetime.now(UTC)))
