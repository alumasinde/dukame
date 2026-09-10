import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.auth.models.identity import User
from app.modules.auth.models.tokens import PasswordResetToken, VerificationToken
from app.modules.auth.security import hash_password, revoke_all_user_sessions
from app.modules.auth.token import expires_in, hash_token, random_token


async def issue_verification_token(db: AsyncSession, user: User) -> str:
    token = random_token()
    db.add(VerificationToken(public_id=uuid.uuid4().hex, user_id=user.id, token_hash=hash_token(token), expires_at=expires_in(24)))
    return token


async def verify_email(db: AsyncSession, token: str) -> None:
    row = await db.scalar(select(VerificationToken).where(VerificationToken.token_hash == hash_token(token)).with_for_update())
    if row is None or row.consumed_at is not None or row.expires_at <= utc_now():
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")
    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired")
    user.is_verified = True
    row.consumed_at = utc_now()


async def issue_password_reset_token(db: AsyncSession, user: User) -> str:
    token = random_token()
    db.add(PasswordResetToken(public_id=uuid.uuid4().hex, user_id=user.id, token_hash=hash_token(token), expires_at=expires_in(1)))
    return token


async def reset_password(db: AsyncSession, token: str, password: str) -> None:
    row = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)).with_for_update())
    if row is None or row.consumed_at is not None or row.expires_at <= utc_now():
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
    user.password_hash = hash_password(password)
    row.consumed_at = utc_now()
    await revoke_all_user_sessions(db, user.id)
