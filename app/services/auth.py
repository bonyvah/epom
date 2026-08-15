from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse
from app.utils.auth import create_access_token, hash_password, verify_password


async def register(body: RegisterRequest, db: AsyncSession) -> TokenResponse:
    user = User(username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Login already taken"
        )

    await db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)))


async def login(body: LoginRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.username == body.username, User.deleted_at.is_(None))
    )
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))
