from fastapi import APIRouter, status

from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse
from app.database import DBSession
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def register(body: RegisterRequest, db: DBSession):
    return await auth_service.register(body, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DBSession):
    return await auth_service.login(body, db)
