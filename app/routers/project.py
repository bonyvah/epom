from fastapi import APIRouter, status

from uuid import UUID

from app.schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate, InviteUserRequest
from app.dependencies import CurrentUser, PaginationParamsDep
from app.database import DBSession
from app.services import project as project_service

router = APIRouter(tags=["projects"])

@router.get("/projects", response_model=list[ProjectResponse])
async def get_projects(pagination:PaginationParamsDep, current_user: CurrentUser, db:DBSession):
    return await project_service.get_projects(pagination,current_user, db)

@router.post("/project", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, current_user: CurrentUser, db: DBSession):
    return await project_service.create_project(body, current_user, db)

@router.get("/project/{id}/info", response_model=ProjectResponse)
async def get_project_info(id: UUID, current_user: CurrentUser, db: DBSession):
    return await project_service.get_project_info(id,current_user, db)

@router.put("/project/{id}/info", response_model=ProjectResponse)
async def update_project_info(id: UUID, body: ProjectUpdate, current_user: CurrentUser, db: DBSession):
    return await project_service.update_project_info(id,body,current_user, db)

@router.delete("/project/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(id: UUID, current_user: CurrentUser, db: DBSession):
    await project_service.delete_project(id,current_user, db)

@router.post("/project/{project_id}/invite", status_code=status.HTTP_201_CREATED)
async def grant_access_to_project(project_id: UUID, body: InviteUserRequest, current_user: CurrentUser, db: DBSession):
    await project_service.grant_access_to_project(project_id, body.user_id, current_user, db)

@router.post("/project/{id}/share", status_code=status.HTTP_202_ACCEPTED)
async def send_join_link(id: UUID, email: str, current_user: CurrentUser, db: DBSession):
    await project_service.send_join_link(id, email, current_user, db)

@router.get("/join")
async def join_project(token: str, current_user: CurrentUser, db: DBSession):
    await project_service.join_project_via_token(token, current_user, db)
