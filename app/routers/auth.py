from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from typing import Annotated

from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse
from app.database import DBSession
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def register(body: RegisterRequest, db: DBSession):
    return await auth_service.register(body, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession
):
    return await auth_service.login(
        LoginRequest(login=form_data.username, password=form_data.password), db
    )
