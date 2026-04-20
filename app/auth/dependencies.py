from uuid import UUID

from auth.jwt import verify_token
from core.exceptions import AppException
from db.session import get_pg_db
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from models import User
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_pg_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    oauth_token: str | None = Depends(oauth2_scheme),
) -> User:

    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif oauth_token:
        token = oauth_token

    if not token:
        raise AppException(
            code="MISSING_CREDENTIALS",
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    try:
        payload = verify_token(token)
    except Exception:
        raise AppException(
            code="INVALID_TOKEN",
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not payload or "sub" not in payload:
        raise AppException(
            code="INVALID_TOKEN",
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError):
        raise AppException(
            code="INVALID_TOKEN",
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier",
        )

    result = await db.scalars(
        select(User).where(User.public_id == user_id)
    )
    user: User | None = result.one_or_none()

    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            status_code=HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise AppException(
            code="USER_INACTIVE",
            status_code=HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    # only trust DB
    request.state.current_user = user
    request.state.current_role = user.role

    return user
