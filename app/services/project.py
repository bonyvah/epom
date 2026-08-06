from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, User, Membership
from app.schemas.project import ProjectCreate


async def create_project(body: ProjectCreate, current_user: User, db: AsyncSession): ...


async def get_projects(current_user: User, db: AsyncSession) -> list[Project]:
    result = await db.execute(
        select(Project)
        .join(Membership, Membership.project_id == Project.id)
        .where(Membership.user_id == current_user.id, Project.deleted_at.is_(None))
    )

    return list(result.scalars().all())
