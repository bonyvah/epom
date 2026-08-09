from fastapi import HTTPException, status
from sqlalchemy import select

from uuid import UUID, uuid4

from app.models import User, Document, Membership, Project
from app.database import AsyncSession
from app.services.project import _get_current_user_project
from app.schemas.document import DocumentCreate
from app.utils.s3 import upload_file, fetch_file, delete_file


async def get_project_documents(
    project_id: UUID, current_user: User, db: AsyncSession
) -> list[Document]:
    project = await _get_current_user_project(project_id, current_user, db)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await db.execute(
        select(Document).where(
            Document.project_id == project_id, Document.deleted_at.is_(None)
        )
    )

    return list(result.scalars().all())


async def upload_documents_to_project(
    project_id: UUID,
    documents: list[DocumentCreate],
    current_user: User,
    db: AsyncSession,
) -> list[Document]:
    project = await _get_current_user_project(project_id, current_user, db)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    docs = []
    for d in documents:
        temp = d.name[::-1]
        if "." not in temp:
            content_type = "raw"
        else:
            content_type = temp[: temp.index(".")]

        key = f"{d.name}_{project_id}"
        try:
            upload_file(key, d.file)
        except:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not upload document",
            )

        document = Document(
            id=uuid4(),
            project_id=project_id,
            name=d.name,
            s3_key=key,
            size_bytes=len(d.file),
            content_type=content_type,
            uploaded_by=current_user.id,
        )
        docs.append(document)
        db.add(document)

    await db.commit()

    for d in docs:
        await db.refresh(d)

    return docs


async def download_file(id: UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(Document)
        .join(Project, Document.project_id == Project.id)
        .join(Membership, Project.id == Membership.project_id)
        .where(
            Document.id == id,
            Membership.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )

    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    try:
        file = fetch_file(document.s3_key)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not download document",
            )
        return file
    except:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not download document",
        )


async def delete_document(id: UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(Document)
        .join(Project, Document.project_id == Project.id)
        .join(Membership, Project.id == Membership.project_id)
        .where(
            Document.id == id,
            Membership.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )

    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    try:
        if not delete_file(document.s3_key):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not delete document",
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete document",
        )

    await db.delete(document)
