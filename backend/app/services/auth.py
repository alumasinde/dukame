import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    make_session,
    revoke_all_user_sessions,
    revoke_session,
    token_hash,
    verify_password,
)
from app.core.time import ensure_utc, utc_now
from app.models.identity import AuthSession, Tenant, TenantUser, User


async def register_user(db: AsyncSession, email: str, password: str, first_name: str, last_name: str, phone: str | None) -> User:
    normalized_email = email.strip().lower()
    normalized_phone = phone.strip() if phone else None
    if await db.scalar(select(User).where(User.email == normalized_email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    if normalized_phone and await db.scalar(select(User).where(User.phone == normalized_phone)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already registered")
    user = User(public_id=uuid.uuid4().hex, email=normalized_email, phone=normalized_phone, password_hash=hash_password(password), first_name=first_name.strip(), last_name=last_name.strip())
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account details are already in use") from exc
    return user


async def authenticate(db: AsyncSession, email: str, password: str, user_agent: str | None, ip_address: str | None) -> tuple[User, AuthSession, str]:
    user = await db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    session, refresh = make_session(user, user_agent, ip_address)
    user.last_login_at = utc_now()
    db.add(session)
    await db.flush()
    return user, session, refresh


async def rotate_refresh_token(db: AsyncSession, refresh_token: str, user_agent: str | None, ip_address: str | None) -> tuple[User, AuthSession, str]:
    session = await db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash(refresh_token)).with_for_update())
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if session.revoked_at is not None or ensure_utc(session.expires_at) <= utc_now():
        await revoke_all_user_sessions(db, user.id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is no longer valid")
    revoke_session(session)
    new_session, new_refresh = make_session(user, user_agent, ip_address)
    db.add(new_session)
    await db.flush()
    return user, new_session, new_refresh


async def logout(db: AsyncSession, session_public_id: str, user_id: int) -> None:
    session = await db.scalar(select(AuthSession).where(AuthSession.public_id == session_public_id, AuthSession.user_id == user_id).with_for_update())
    if session:
        revoke_session(session)


async def get_user_tenants(db: AsyncSession, user_id: int) -> list[tuple[Tenant, TenantUser]]:
    result = await db.execute(select(Tenant, TenantUser).join(TenantUser, TenantUser.tenant_id == Tenant.id).where(TenantUser.user_id == user_id, TenantUser.status == "active").order_by(Tenant.name))
    return [(row[0], row[1]) for row in result.all()]
