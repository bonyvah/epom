from fastapi import APIRouter, UploadFile, File, status

from typing import Annotated, List
from uuid import UUID

from app.schemas.document import DocumentUpdate, DocumentResponse #, UploadDocumentsResponse
from app.services import document as document_service
from app.dependencies import CurrentUser, PaginationParamsDep
from app.database import DBSession

router = APIRouter(tags=["document"])


@router.get("/project/{id}/documents", response_model=list[DocumentResponse])
async def get_project_documents(id: UUID,pagination:PaginationParamsDep, current_user: CurrentUser, db: DBSession):
    return await document_service.get_project_documents(id,pagination, current_user, db)

@router.post("/project/{id}/document", response_model=DocumentResponse)
async def upload_document_to_project(id: UUID, file: UploadFile, current_user: CurrentUser, db:DBSession):
    return await document_service.upload_document_to_project(id, file, current_user,db)

@router.put("/document/{id}", response_model=DocumentResponse)
async def update_document(id: UUID, body: DocumentUpdate, current_user: CurrentUser, db: DBSession):
    return await document_service.update_document(id, body, current_user, db)

@router.get("/document/{id}", response_model=dict)
async def download_file(id: UUID, current_user: CurrentUser, db: DBSession):
    return await document_service.download_file(id, current_user, db)

@router.delete("/document/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(id: UUID, current_user: CurrentUser, db: DBSession):
    await document_service.delete_document(id, current_user, db)

# @router.post(
#     "/project/{id}/documents",
#     response_model=UploadDocumentsResponse,
#     openapi_extra={
#         "requestBody": {
#             "content": {
#                 "multipart/form-data": {
#                     "schema": {
#                         "type": "object",
#                         "required": ["files"],
#                         "properties": {
#                             "files": {
#                                 "type": "array",
#                                 "items": {"type": "string", "format": "binary"},
#                                 "description": "Files to upload",
#                             }
#                         },
#                     }
#                 }
#             },
#             "required": True,
#         }
#     },
# )
# async def upload_project_documents(id: UUID, current_user: CurrentUser, db: DBSession, files: Annotated[List[UploadFile], File(description="Files to upload")]):
#     return await document_service.upload_documents_to_project(id, files, current_user, db)
