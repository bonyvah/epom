from fastapi import APIRouter

from app.schemas.project import ProjectResponse
from app.dependencies import CurrentUser
from app.database import DBSession
from app.services import project

router = APIRouter(tags=["projects"])

@router.get("/projects", response_model=list[ProjectResponse])
async def get_projects(current_user: CurrentUser, db:DBSession):
    return await project.get_projects(current_user, db)