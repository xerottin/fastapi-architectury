import logging
from uuid import UUID

from core.exceptions import AppException
from services.base import get_by_public_id, get_by_id
from models import Project, User
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.cache.project_cache import ProjectCache

logger = logging.getLogger(__name__)


async def create_project(
    payload: ProjectCreate,
    db: AsyncSession,
    current_user: User,
) -> Project:
    print(f"current_user: {current_user.id}, project: {current_user.project_id}")
    exist_project = await db.scalar(
        select(Project).where(
            Project.name == payload.name,
            Project.owner_id == current_user.id,
            Project.is_active,
        )
    )

    if exist_project:
        raise AppException(
            code="PROJECT_NAME_EXISTS",
            i18n_key="errors.project_name_exists",
            status_code=409,
            detail="Project with this name already exists",
        )

    try:
        project = Project(
            name=payload.name,
            description=payload.description,
            owner_id=current_user.id,
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)
        await ProjectCache.invalidate(current_user.id)

        return project

    except AppException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error creating project")
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Internal server error",
        ) from e


async def get_owned_project(
    public_id: UUID,
    db: AsyncSession,
    user_id: int,
) -> Project:
    project = await get_by_public_id(db, Project, public_id)

    if project.owner_id != user_id:
        raise AppException(
            code="PROJECT_NOT_FOUND",
            i18n_key="errors.project_not_found",
            status_code=404,
            detail="Project not found",
        )

    return project


async def get_project_users(
    db: AsyncSession,
    *,
    public_id: UUID | None = None,
    private_id: int | None = None,
) -> list[User]:

    if not public_id and not private_id:
        return []

    if public_id and private_id:
        raise AppException(
            code="AMBIGUOUS_PROJECT_ID",
            i18n_key="errors.invalid_request",
            status_code=400,
            detail="Provide either public_id or private_id, not both",
        )

    project = await get_by_public_id(db, Project, public_id) if public_id else await get_by_id(db, Project, private_id)

    if not project:
        return []

    result = await db.scalars(
        select(User)
        .where(
            User.project_id == project.id,
            User.is_active.is_(True),
        )
        .order_by(User.id)
    )

    return result.all()


async def get_project_id_by_public_id(
    public_id: UUID,
    db: AsyncSession,
):
    project_public_id = (
        await db.execute(
            select(Project).where(
                Project.public_id == public_id,
                Project.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not project_public_id:
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Project not found",
        )
    return project_public_id.id


async def list_projects(db: AsyncSession, current_user: User) -> list[Project]:
    cached = await ProjectCache.get(current_user.id)
    if cached is not None:
        return [ProjectResponse(**item) for item in cached]

    result = await db.execute(
        select(Project).where(
            Project.owner_id == current_user.id,
            Project.is_active.is_(True),
        )
    )
    projects = result.scalars().all()

    serialized = [ProjectResponse.model_validate(p).model_dump(mode="json") for p in projects]
    await ProjectCache.set(current_user.id, serialized)
    return projects


async def get_project(
    public_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> Project:
    return await get_owned_project(
        public_id=public_id,
        db=db,
        user_id=current_user.id,
    )


async def update_project(
    public_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession,
    current_user: User,
) -> Project:
    project = await get_owned_project(
        public_id=public_id,
        db=db,
        user_id=current_user.id,
    )

    try:
        update_data = payload.model_dump(exclude_unset=True)

        if "owner_public_id" in update_data:
            owner_public_id = update_data.pop("owner_public_id")
            owner = await get_by_public_id(db, User, owner_public_id)
            update_data["owner_id"] = owner.id

        for key, value in update_data.items():
            setattr(project, key, value)

        await db.commit()
        await db.refresh(project)
        await ProjectCache.invalidate(current_user.id)

        return project

    except AppException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error updating project")
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Internal server error",
        ) from e


async def delete_project(
    public_id: UUID,
    db: AsyncSession,
    current_user: User,
):
    project = await get_owned_project(
        public_id=public_id,
        db=db,
        user_id=current_user.id,
    )

    if not project.is_active:
        raise AppException(
            code="PROJECT_ALREADY_DEACTIVATED",
            i18n_key="errors.project_already_deactivated",
            status_code=400,
            detail="Project already deactivated",
        )

    try:
        project.is_active = False
        await db.commit()
        await ProjectCache.invalidate(current_user.id)

    except AppException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Error deleting project")
        raise AppException(
            code="INTERNAL_ERROR",
            i18n_key="errors.internal_server_error",
            status_code=500,
            detail="Internal server error",
        ) from e
