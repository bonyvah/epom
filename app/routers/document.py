from fastapi import APIRouter, UploadFile, File, status

from typing import Annotated
from uuid import UUID

from app.schemas.document import DocumentUpdate, DocumentResponse
from app.services import document as document_service
from app.dependencies import CurrentUser
from app.database import DBSession

router = APIRouter(tags=["document"])


@router.get("/project/{id}/documents", response_model=list[DocumentResponse])
async def get_project_documents(id: UUID, current_user: CurrentUser, db: DBSession):
    return await document_service.get_project_documents(id, current_user, db)


@router.post("/project/{id}/documents", response_model=list[DocumentResponse])
async def upload_project_documents(id: UUID, current_user: CurrentUser, db: DBSession, files: Annotated[list[UploadFile], File(...)]):
    return await document_service.upload_documents_to_project(id, files, current_user, db)


@router.get("/documents/{id}")
async def download_file(id: UUID, current_user: CurrentUser, db: DBSession):
    return await document_service.download_file(id, current_user, db)

@router.delete("/document/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(id: UUID, current_user: CurrentUser, db: DBSession):
    await document_service.delete_document(id, current_user, db)
