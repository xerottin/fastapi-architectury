from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from core.config import settings
from jose import ExpiredSignatureError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Any, expires_delta: timedelta | None = None) -> str:
    if hasattr(data, "model_dump"):
        to_encode = data.model_dump()
    elif hasattr(data, "dict"):
        to_encode = data.dict()
    else:
        to_encode = dict(data)

    for key, value in to_encode.items():
        if hasattr(value, "value"):
            to_encode[key] = value.value
        elif isinstance(value, datetime):
            to_encode[key] = value.isoformat()

    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: Any) -> str:
    if hasattr(data, "model_dump"):
        to_encode = data.model_dump()
    elif hasattr(data, "dict"):
        to_encode = data.dict()
    else:
        to_encode = dict(data)

    for key, value in to_encode.items():
        if hasattr(value, "value"):
            to_encode[key] = value.value
        elif isinstance(value, datetime):
            to_encode[key] = value.isoformat()

    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_refresh_token_expire_hours)
    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(
    token: str, secret: str | None = None, audience: str | None = None, expected_type: str | None = None
) -> dict:
    secret = secret or settings.jwt_secret_key

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            audience=audience,
        )

        if expected_type and payload.get("type") != expected_type:
            raise ValueError(f"Invalid token type: expected '{expected_type}', got '{payload.get('type')}'")

        return payload

    except ExpiredSignatureError as e:
        raise ValueError("Token has expired") from e


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

