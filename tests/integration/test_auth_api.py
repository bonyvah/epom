import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    assert response.json()["detail"] == "Username already taken"


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


@pytest.mark.asyncio
async def test_login_soft_deleted_user(client: AsyncClient, db_session: AsyncSession, test_user: User):
    from datetime import UTC, datetime
    test_user.deleted_at = datetime.now(UTC)
    db_session.add(test_user)
    await db_session.commit()

    form_data = {
        "username": test_user.username,
        "password": "testpassword123"
    }

    response = await client.post("/login", data=form_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_jwt_invalid_sub_cases(client: AsyncClient):
    import jwt
    from datetime import UTC, datetime, timedelta
    import uuid
    from app.config import settings

    def make_token(sub_val):
        expire = datetime.now(UTC) + timedelta(minutes=10)
        payload = {"exp": expire}
        if sub_val is not None:
            payload["sub"] = sub_val
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    # 1. Missing sub claim
    t_missing = make_token(None)
    res = await client.get("/projects", headers={"Authorization": f"Bearer {t_missing}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid or expired token"

    # 2. Empty sub claim
    t_empty = make_token("")
    res = await client.get("/projects", headers={"Authorization": f"Bearer {t_empty}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid or expired token"

    # 3. Invalid UUID in sub claim
    t_invalid_uuid = make_token("not-a-uuid-at-all")
    res = await client.get("/projects", headers={"Authorization": f"Bearer {t_invalid_uuid}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid or expired token"

    # 4. Valid UUID for nonexistent user
    t_nonexistent_user = make_token(str(uuid.uuid4()))
    res = await client.get("/projects", headers={"Authorization": f"Bearer {t_nonexistent_user}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "User not found"