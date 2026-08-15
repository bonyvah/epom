import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    payload = {
        "username": "newuser@example.com",
        "password": "strongpassword123",
        "repeat_password": "strongpassword123"
    }

    response = await client.post("/auth", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify db record
    result = await db_session.execute(
        select(User).where(User.username == "newuser@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None


@pytest.mark.asyncio
async def test_register_passwords_mismatch(client: AsyncClient):
    payload = {
        "username": "mismatch@example.com",
        "password": "strongpassword123",
        "repeat_password": "differentpassword"
    }

    response = await client.post("/auth", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user: User):
    payload = {
        "username": test_user.username,
        "password": "somepassword123",
        "repeat_password": "somepassword123"
    }

    response = await client.post("/auth", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    form_data = {
        "username": test_user.username,
        "password": "testpassword123"
    }

    response = await client.post("/login", data=form_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User):
    form_data = {
        "username": test_user.username,
        "password": "wrongpassword"
    }

    response = await client.post("/login", data=form_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    form_data = {
        "username": "nonexistent@example.com",
        "password": "somepassword"
    }

    response = await client.post("/login", data=form_data)
    assert response.status_code == 401