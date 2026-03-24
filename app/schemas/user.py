from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)

# ============================================================
# Base ORM config
# ============================================================


class OrmBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # allow ORM objects
        populate_by_name=True,
        use_enum_values=True,  # enum -> str
        extra="ignore",  # ignore unknown fields
    )



# ============================================================
# Shared fields
# ============================================================


class UserBase(OrmBase):
    username: str | None = None
    email: str | None = None


# ============================================================
# Password validation
# ============================================================


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return password


# ============================================================
# Input DTOs (requests)
# ============================================================


class UserRegisterRequest(BaseModel):
    """
    Public registration
    """

    email: str | None = None
    username: str | None = None
    password: str
    role: str = "default_user"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided")
        return self


class UserCreateRequest(BaseModel):

    email: str | None = None
    username: str | None = None
    password: str
    role: str = "default_user"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

class UserSingInRequest(BaseModel):
    email: str | None = None
    username: str = None
    password: str = None


class UserUpdateRequest(BaseModel):

    email: str | None = None
    username: str | None = None
    password: str | None = None
    role: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_password_strength(v)


# ============================================================
# Output DTOs (responses)
# ============================================================


class UserLoginSchemas(BaseModel):
    email: str
    password: str


class UserResponse(UserBase):
    public_id: UUID
    role: str | None = None
    created_at: datetime
    updated_at: datetime


class UserShortResponse(OrmBase):
    public_id: UUID
    email: str | None = None
    role: str | None = None


# ============================================================
# Auth / Tokens
# ============================================================


class TokensResponse(OrmBase):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(OrmBase):
    user: UserResponse
    tokens: TokensResponse
