import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app
from app.models import Membership, Project, Role, User
from app.utils.auth import create_access_token, hash_password

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/epom_test"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio's event_loop fixture to run all tests on one loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# --- Simple Session Fixture ---
@pytest_asyncio.fixture()
async def db_session():
    async with TestSessionLocal() as session:
        yield session


# --- Autouse Database Cleaner ---
@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """Wipes all data from tables after every test to keep tests isolated."""
    yield
    async with test_engine.begin() as conn:
        # Truncate tables in reverse order of dependencies to avoid constraint violations
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE;"))


# --- Rest of fixtures (client, mock_s3_and_mail, test_user, auth_headers, test_project) stay the same ---
@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_s3_and_mail():
    with patch("app.services.document.upload_file", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.document.delete_file", new_callable=AsyncMock) as mock_delete, \
         patch("app.services.document.generate_presigned_url", new_callable=AsyncMock) as mock_presign, \
         patch("app.services.project.send_mail", new_callable=AsyncMock) as mock_send_mail, \
         patch("app.services.project.delete_file", new_callable=AsyncMock) as mock_proj_delete:
        
        mock_presign.return_value = "https://mocked-s3-presigned-url.com/file"
        
        yield {
            "upload_file": mock_upload,
            "delete_file": mock_delete,
            "generate_presigned_url": mock_presign,
            "send_mail": mock_send_mail,
            "project_delete_file": mock_proj_delete,
        }


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        username="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    project = Project(
        name="Test Project",
        description="A project for integration testing",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.flush()
    
    membership = Membership(
        project_id=project.id,
        user_id=test_user.id,
        role=Role.owner
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(project)
    return project