from uuid import UUID

from fastapi import APIRouter, Depends
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from services.user import create_user, update_user, delete_user, get_login_user
from db.session import get_pg_db
from models import User
from schemas.user import AuthResponse, UserCreateRequest, UserResponse, UserUpdateRequest, UserLoginSchemas

router = APIRouter()

@router.post("", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_pg_db),
):
    return await create_user(db, payload)

@router.post("/sign-in", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def login_endpoint(
        data: UserLoginSchemas,
        db: AsyncSession = Depends(get_pg_db),
):
    return await get_login_user(data, db)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/{public_id}", response_model=UserResponse)
async def update_user_endpoint(
    public_id: UUID,
    user: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    return await update_user(db, public_id, user)


@router.delete("/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    public_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    await delete_user(db, public_id)

