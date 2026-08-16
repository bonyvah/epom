from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.database import AsyncSession
from app.models import Document, Membership, Project, User
from app.schemas.document import DocumentUpdate
from app.schemas.pagination import PaginationParams
from app.services.project import _get_current_user_project
from app.utils.file import validate_and_infer_mime
from app.utils.s3 import delete_file, generate_presigned_url, upload_file


async def _get_current_user_document(id: UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(Document)
        .join(Project, Document.project_id == Project.id)
        .join(Membership, Project.id == Membership.project_id)
        .where(
            Document.id == id,
            Membership.user_id == current_user.id,
        )
    )

    return result.scalar_one_or_none()


async def get_project_documents(
    project_id: UUID, pagination: PaginationParams, current_user: User, db: AsyncSession
) -> list[Document]:
    project = await _get_current_user_project(project_id, current_user, db)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .offset(pagination.offset)
        .limit(pagination.size)
    )

    return list(result.scalars().all())


async def upload_document_to_project(
    project_id: UUID, file: UploadFile, current_user: User, db: AsyncSession
) -> Document:
    # 1. access check
    project = await _get_current_user_project(project_id, current_user, db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Read the file contents
    contents = await file.read()
    await file.seek(0)
    file_size = len(contents)

    # 2. Magic Bytes & Type Validation (Using the utility)
    try:
        validate_and_infer_mime(file.filename or "", contents)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 3. size checks
    if file_size > project.document_size_limit_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds project document limit of {project.document_size_limit_mb}MB",
        )

    # check project limit
    total_size_query = await db.execute(
        select(func.sum(Document.size_bytes)).where(Document.project_id == project_id)
    )
    current_total = total_size_query.scalar() or 0

    if current_total + file_size > project.project_size_limit_gb * 1024 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Upload would exceed project total size limit of {project.project_size_limit_gb}GB",
        )

    # 4. s3 upload
    document_id = uuid4()
    key = f"{document_id}/{file.filename}"
    content_type = file.content_type or "application/octet-stream"

    try:
        await upload_file(key, contents, content_type)
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to upload file",
        )

    # 5. save to db
    document = Document(
        id=document_id,
        project_id=project_id,
        name=file.filename,
        s3_key=key,
        size_bytes=file_size,
        content_type=content_type,
        uploaded_by=current_user.id,
    )
    db.add(document)
    try:
        await db.commit()
        await db.refresh(document)
    except Exception:
        await db.rollback()
        try:
            await delete_file(key)
        except Exception:  # noqa: BLE001, S110
            pass
        raise

    return document


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


async def update_document(
    id: UUID, body: DocumentUpdate, current_user: User, db: AsyncSession
) -> Document:
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
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to delete file",
        )
    await db.delete(document)
    await db.commit()


# async def upload_documents_to_project(
#     project_id: UUID,
#     files: list[UploadFile],
#     current_user: User,
#     db: AsyncSession,
# ) -> dict:
#     #1)
#     project = await _get_current_user_project(project_id, current_user, db)

#     if not project:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
#         )

#     doc_limit_bytes = project.document_size_limit_mb * 1024 * 1024
#     project_limit_bytes = project.project_size_limit_gb * 1024 * 1024 * 1024

#     total_size_query = await db.execute(
#         select(func.sum(Document.size_bytes)).where(Document.project_id == project_id)
#     )
#     current_total_size = total_size_query.scalar() or 0

#     docs = []
#     uploaded_keys = []
#     for file in files:
#         contents = await file.read()

#         if len(contents) > doc_limit_bytes:
#             raise HTTPException(
#                 status_code=status.HTTP_413_CONTENT_TOO_LARGE,
#                 detail=f"File {file.filename} exceeds project document limit of {project.document_size_limit_mb}MB",
#             )

#         document_id = uuid4()
#         key = f"{document_id}/{file.filename}"
#         content_type = file.content_type or "application/octet-stream"

#         try:
#             await upload_file(key, contents, content_type)
#             uploaded_keys.append(key)
#         except Exception:
#             for key in uploaded_keys:
#                 await delete_file(key)
#             raise HTTPException(
#                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#                 detail=f"Failed to upload {file.filename}",
#             )

#         document = Document(
#             id=document_id,
#             project_id=project_id,
#             name=file.filename,
#             s3_key=key,
#             size_bytes=len(contents),
#             content_type=content_type,
#             uploaded_by=current_user.id,
#         )
#         docs.append(document)
#         db.add(document)

#     await db.commit()

#     for d in docs:
#         await db.refresh(d)

#     return docs
