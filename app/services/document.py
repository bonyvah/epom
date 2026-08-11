from fastapi import HTTPException, status, UploadFile

from sqlalchemy import select

from uuid import UUID, uuid4

from app.models import User, Document, Membership, Project
from app.database import AsyncSession
from app.services.project import _get_current_user_project
from app.schemas.document import DocumentUpdate
from app.utils.s3 import upload_file,  delete_file, generate_presigned_url
from app.config import settings

async def _get_current_user_document(id: UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
            select(Document)
            .join(Project, Document.project_id == Project.id)
            .join(Membership, Project.id == Membership.project_id)
            .where(
                Document.id == id,
                Membership.user_id == current_user.id,
                Project.deleted_at.is_(None)
            )
        )
    
    return result.scalar_one_or_none()

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
            Document.project_id == project_id
        )
    )

    return list(result.scalars().all())

async def upload_documents_to_project(
    project_id: UUID,
    files: list[UploadFile],
    current_user: User,
    db: AsyncSession,
) -> list[Document]:
    project = await _get_current_user_project(project_id, current_user, db)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    docs = []
    uploaded_keys = []
    for file in files:
        contents = await file.read()

        if len(contents) > settings.file_size_limit_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{file.filename} exceeds {settings.file_size_limit_mb}MB limit")

        document_id = uuid4()
        key = f"{document_id}/{file.filename}"
        content_type = file.content_type or "application/octet-stream"

        try:
            await upload_file(key, contents, content_type)
            uploaded_keys.append(key)
        except Exception:
            for key in uploaded_keys:
                await delete_file(key)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to upload {file.filename}"
            )

        document = Document(
            id=document_id,
            project_id=project_id,
            name=file.filename,
            s3_key=key,
            size_bytes=len(contents),
            content_type=content_type,
            uploaded_by=current_user.id,
        )
        docs.append(document)
        db.add(document)

    await db.commit()

    for d in docs:
        await db.refresh(d)

    return docs

async def download_file(id: UUID, current_user: User, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Document)
        .join(Project, Document.project_id == Project.id)
        .join(Membership, Project.id == Membership.project_id)
        .where(
            Document.id == id,
            Membership.user_id == current_user.id,
        )
    )

    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    url = await generate_presigned_url(document.s3_key)
    return {"download_url": url}

async def update_document(id: UUID,  body: DocumentUpdate, current_user: User, db: AsyncSession) -> Document:
    document = await _get_current_user_document(id, current_user, db)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    document.name = body.name

    await db.commit()
    await db.refresh(document)
    return document

async def delete_document(id: UUID, current_user: User, db: AsyncSession):

    document = await _get_current_user_document(id, current_user, db)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    try:
        await delete_file(document.s3_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to delete file"
        )
    await db.delete(document)
    await db.commit()