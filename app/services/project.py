from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models import Project, User, Membership, Role, Document
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.pagination import PaginationParams
from app.utils.send_mail import send_mail
from app.utils.auth import create_invite_token, decode_invite_token
from app.utils.s3 import delete_file
from app.config import settings


async def _get_current_user_project(
    id: UUID, current_user: User, db: AsyncSession
) -> Project | None:
    result = await db.execute(
        select(Project)
        .join(Membership, Membership.project_id == Project.id)
        .where(
            Membership.user_id == current_user.id,
            Project.id == id,
            Project.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_project(
    body: ProjectCreate, current_user: User, db: AsyncSession
) -> Project:

    project_id = uuid4()

    project = Project(
        id=project_id,
        name=body.name,
        description=body.description,
        owner_id=current_user.id,
    )

    membership = Membership(
        project_id=project_id, user_id=current_user.id, role=Role.owner
    )

    db.add(project)
    await db.flush()
    db.add(membership)
    await db.commit()
    await db.refresh(project)

    return project


async def get_projects(
    pagination: PaginationParams, current_user: User, db: AsyncSession
) -> list[Project]:
    result = await db.execute(
        select(Project)
        .join(Membership, Membership.project_id == Project.id)
        .where(Membership.user_id == current_user.id, Project.deleted_at.is_(None))
        .offset(pagination.offset)
        .limit(pagination.size)
    )

    return list(result.scalars().all())


async def get_project_info(id: UUID, current_user: User, db: AsyncSession) -> Project:
    project = await _get_current_user_project(id, current_user, db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )
    return project


async def update_project_info(
    id: UUID, body: ProjectUpdate, current_user: User, db: AsyncSession
) -> Project:
    project = await _get_current_user_project(id, current_user, db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )

    update_data = body.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)

    return project


async def delete_project(id: UUID, current_user: User, db: AsyncSession) -> None:

    project = await _get_current_user_project(id, current_user, db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Such project does not exist",
        )
    if not project.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners of the project allowed to delete it",
        )

    doc_result = await db.execute(select(Document).where(Document.project_id == id))
    member_result = await db.execute(
        select(Membership).where(Membership.project_id == id)
    )
    documents = doc_result.scalars().all()
    members = member_result.scalars().all()
    keys = [d.s3_key for d in documents]

    project.deleted_at = datetime.now(timezone.utc)
    for d in documents:
        await db.delete(d)
    for m in members:
        await db.delete(m)
    await db.commit()

    for k in keys:
        await delete_file(k)


async def grant_access_to_project(
    project_id: UUID, user_id: UUID, current_user: User, db: AsyncSession
) -> None:
    project = await _get_current_user_project(project_id, current_user, db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Such project does not exist",
        )
    if not project.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners of the project allowed to grant access",
        )

    user_exists = await db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    member_exists = await db.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.project_id == project_id
        )
    )

    if member_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user is already member of the project",
        )

    membership = Membership(
        project_id=project_id, user_id=user_id, role=Role.participant
    )

    db.add(membership)
    await db.commit()


async def send_join_link(
    project_id: UUID, email: str, current_user: User, db: AsyncSession
) -> None:
    project = await _get_current_user_project(project_id, current_user, db)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You dont have enough permissions",
        )

    invite_token = create_invite_token(str(project_id), email)
    link = f"{settings.app_url}/join?token={invite_token}"

    await send_mail(
        settings.sender_email, email, "Join the project: " + project.name, link
    )


async def join_project_via_token(
    token: str, current_user: User, db: AsyncSession
) -> None:
    project_id = UUID(decode_invite_token(token))

    if await _get_current_user_project(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Already member"
        )

    membership = Membership(
        project_id=project_id, user_id=current_user.id, role=Role.participant
    )

    db.add(membership)
    await db.commit()
    await db.refresh(membership)
