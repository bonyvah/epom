from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, Project, Role, User
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


@pytest.mark.asyncio
async def test_get_project_info_success(client: AsyncClient, auth_headers: dict, test_project: Project):
    response = await client.get(f"/project/{test_project.id}/info", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_project_info_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get(f"/project/{uuid4()}/info", headers=auth_headers)
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

    # Verify project is hard-deleted from the database
    result = await db_session.execute(
        select(Project).where(Project.id == test_project.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_project_forbidden_for_non_owner(client: AsyncClient, test_project: Project, db_session: AsyncSession):
    # Create another user and get their headers
    other_user = User(username="other@example.com", hashed_password=hash_password("password"))
    db_session.add(other_user)
    await db_session.commit()
    from app.utils.auth import create_access_token
    token = create_access_token(str(other_user.id))
    other_headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete test_project owned by test_user
    response = await client.delete(f"/project/{test_project.id}", headers=other_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_grant_access_to_project(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession):
    another_user = User(username="invited@example.com", hashed_password=hash_password("password123"))
    db_session.add(another_user)
    await db_session.commit()

    payload = {"user_id": str(another_user.id)}
    response = await client.post(f"/project/{test_project.id}/invite", json=payload, headers=auth_headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_grant_access_already_member(client: AsyncClient, auth_headers: dict, test_project: Project, test_user: User):
    # Try to invite ourselves (already owner/member)
    payload = {"user_id": str(test_user.id)}
    response = await client.post(f"/project/{test_project.id}/invite", json=payload, headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_send_join_link_success(client: AsyncClient, auth_headers: dict, test_project: Project, mock_s3_and_mail: dict):
    email = "new_member@example.com"
    response = await client.post(f"/project/{test_project.id}/share", json={"email": email}, headers=auth_headers)
    assert response.status_code == 202
    assert mock_s3_and_mail["send_mail"].called


@pytest.mark.asyncio
async def test_join_project_flow(client: AsyncClient, auth_headers: dict, test_project: Project, mock_s3_and_mail: dict, db_session: AsyncSession):
    # 1. Invite a member
    email = "invitee@example.com"
    response = await client.post(f"/project/{test_project.id}/share", json={"email": email}, headers=auth_headers)
    assert response.status_code == 202

    # 2. Extract invite link and token from mock mail call
    assert mock_s3_and_mail["send_mail"].called
    call_args = mock_s3_and_mail["send_mail"].call_args[0]
    link = call_args[3]
    
    import urllib.parse
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    token = params["token"][0]

    # 3. Create a new user (invitee)
    invitee = User(username=email, hashed_password=hash_password("inviteepass"))
    db_session.add(invitee)
    await db_session.commit()

    from app.utils.auth import create_access_token
    invitee_token = create_access_token(str(invitee.id))
    invitee_headers = {"Authorization": f"Bearer {invitee_token}"}

    # 4. Join project using the token
    join_res = await client.get("/join", params={"token": token}, headers=invitee_headers)
    assert join_res.status_code == 200

    # 5. Verify the invitee is now a member of the project
    info_res = await client.get(f"/project/{test_project.id}/info", headers=invitee_headers)
    assert info_res.status_code == 200
    assert info_res.json()["id"] == str(test_project.id)


@pytest.mark.asyncio
async def test_join_project_expired_token(client: AsyncClient, test_project: Project, db_session: AsyncSession):
    # 1. Create a new user
    invitee = User(username="expired@example.com", hashed_password=hash_password("password"))
    db_session.add(invitee)
    await db_session.commit()

    from app.utils.auth import create_access_token
    invitee_token = create_access_token(str(invitee.id))
    invitee_headers = {"Authorization": f"Bearer {invitee_token}"}

    # 2. Generate expired token
    import jwt
    from datetime import UTC, datetime, timedelta
    from app.config import settings
    expire = datetime.now(UTC) - timedelta(hours=1)
    payload = {"sub": "invite", "project_id": str(test_project.id), "email": "expired@example.com", "exp": expire}
    expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    # 3. Try to join
    response = await client.get("/join", params={"token": expired_token}, headers=invitee_headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired invitation token"