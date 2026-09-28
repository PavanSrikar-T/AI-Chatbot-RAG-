from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

async def get_current_user(
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    email = x_user_email or "dev@local.host"
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        user = User(
            email=email,
            hashed_password="fake",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
