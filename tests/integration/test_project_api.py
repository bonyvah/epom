import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.models import Project, Membership, Role, User
from app.utils.auth import hash_password

@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    payload = {
        "name": "My New Project",
        "description": "Integration testing project creation"
    }

    response = await client.post("/project", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My New Project"
    assert data["description"] == "Integration testing project creation"
    
    result = await db_session.execute(
        select(Membership).where(Membership.project_id == data["id"])
    )
    memberships = result.scalars().all()
    assert len(memberships) == 1
    assert memberships[0].role == Role.owner


@pytest.mark.asyncio
async def test_get_projects_list(client: AsyncClient, auth_headers: dict, test_project: Project):
    response = await client.get("/projects", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_project_info_success(client: AsyncClient, auth_headers: dict, test_project: Project):
    response = await client.get(f"/project/{test_project.id}/info", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_project_info_not_found(client: AsyncClient, auth_headers: dict):
    random_uuid = uuid4()
    response = await client.get(f"/project/{random_uuid}/info", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project_info(client: AsyncClient, auth_headers: dict, test_project: Project):
    payload = {"name": "Updated Project Name"}
    
    response = await client.put(f"/project/{test_project.id}/info", json=payload, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project Name"


@pytest.mark.asyncio
async def test_delete_project_owner_only(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession):
    response = await client.delete(f"/project/{test_project.id}", headers=auth_headers)

    assert response.status_code == 204

    result = await db_session.execute(
        select(Project).where(Project.id == test_project.id)
    )
    project = result.scalar_one_or_none()
    assert project is None or project.deleted_at is not None


@pytest.mark.asyncio
async def test_grant_access_to_project(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession):
    another_user = User(
        username="invited@example.com",
        hashed_password=hash_password("password123")
    )
    db_session.add(another_user)
    await db_session.commit()

    payload = {"user_id": str(another_user.id)}
    
    response = await client.post(
        f"/project/{test_project.id}/invite", 
        json=payload, 
        headers=auth_headers
    )

    assert response.status_code == 201

    result = await db_session.execute(
        select(Membership).where(
            Membership.project_id == test_project.id,
            Membership.user_id == another_user.id
        )
    )
    membership = result.scalar_one_or_none()
    assert membership is not None
    assert membership.role == Role.participant


@pytest.mark.asyncio
async def test_send_join_link_sends_email(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project, 
    mock_s3_and_mail: dict
):
    email = "new_member@example.com"
    response = await client.post(
        f"/project/{test_project.id}/share", 
        params={"email": email}, 
        headers=auth_headers
    )

    assert response.status_code == 202
    
    mock_send_mail = mock_s3_and_mail["send_mail"]
    assert mock_send_mail.called
    call_args = mock_send_mail.call_args[0]
    assert call_args[1] == email  
    assert "Join the project" in call_args[2] 
