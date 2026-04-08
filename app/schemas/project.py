from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectBase(OrmBase):
    public_id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectResponse(ProjectBase):
    name: str
    description: str | None = None
    owner_public_id: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    owner_public_id: int | None = None
