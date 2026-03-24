import logging
import re
import uuid
from uuid import UUID

from auth.jwt import create_access_token, create_refresh_token, hash_password, verify_password
from core.exceptions import AppException
from services.base import get_by_public_id
from models.user import User
from schemas.user import UserCreateRequest, UserLoginSchemas, UserUpdateRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def create_user(db: AsyncSession, data: UserCreateRequest) -> User:
    try:
        existing_user = await db.scalar(select(User).where(User.email == data.email, User.is_active))
        if existing_user:
            raise AppException(
                code="EMAIL_ALREADY_REGISTERED",
                i18n_key="errors.email_already_registered",
                status_code=409,
                detail="Email already registered",
            )

        if not data.username:
            base = re.split(r"@+", data.email)[0]
            base = re.sub(r"\W+", "", base) or "user"
            username = f"{base}_{uuid.uuid1().hex[:4]}"
        else:
            username = data.username

        existing_username = await db.scalar(select(User).where(User.username == username))
        if existing_username:
            username = f"{username}_{uuid.uuid1().hex[:6]}"

        user = User(username=username, email=data.email, hashed_password=hash_password(data.password), role=data.role)

        db.add(user)
        await db.flush()

        # Use public_id for tokens now
        token_data = {"sub": str(user.public_id), "role": data.role}

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        await db.commit()
        await db.refresh(user)

        return {"user": user, "tokens": {"access_token": access_token, "refresh_token": refresh_token}}

    except AppException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error in create_user")
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Internal server error",
        ) from e


async def get_login_user(data: UserLoginSchemas, db: AsyncSession):
    user = await db.scalar(select(User).where(User.email == data.email, User.is_active))
    if not user:
        raise AppException(
            code="INVALID_CREDENTIALS",
            i18n_key="errors.invalid_email_or_password",
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(data.password, user.hashed_password):
        raise AppException(
            code="INVALID_CREDENTIALS",
            status_code=401,
            detail="Invalid email or password",
        )

    # Use public_id for tokens
    token_data = {"sub": str(user.public_id), "role": user.role}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {"user": user, "tokens": {"access_token": access_token, "refresh_token": refresh_token}}


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(User).where(User.is_active == True).offset(skip).limit(limit))
    return result.scalars().all()


async def get_user(db: AsyncSession, public_id: UUID) -> User:
    return await get_by_public_id(db, User, public_id)


async def update_user(db: AsyncSession, public_id: UUID, user_update: UserUpdateRequest) -> User:
    try:
        user = await get_user(db, public_id)

        protected_fields = {"id", "public_id", "created_at", "hashed_password"}
        update_data = user_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if key not in protected_fields:
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user

    except AppException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error updating user %s", public_id)
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Internal server error",
        ) from e


async def delete_user(db: AsyncSession, public_id: UUID):
    user = await get_user(db, public_id)

    if user.is_active:
        user.is_active = False
        await db.commit()
        await db.refresh(user)
