import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models import Project, Document, User
from app.utils.auth import hash_password

@pytest.mark.asyncio
async def test_upload_document_success(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project, 
    mock_s3_and_mail: dict,
    db_session: AsyncSession
):
    file_content = b"This is a test document content."
    files = {"file": ("test.txt", file_content, "text/plain")}

    response = await client.post(
        f"/project/{test_project.id}/document", 
        files=files, 
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test.txt"
    assert mock_s3_and_mail["upload_file"].called


@pytest.mark.asyncio
async def test_upload_document_limit_exceeded(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project, 
    db_session: AsyncSession
):
    # Set document limit to 1MB
    test_project.document_size_limit_mb = 1
    db_session.add(test_project)
    await db_session.commit()

    # Upload a 2MB file (2 * 1024 * 1024 bytes)
    file_content = b"0" * (2 * 1024 * 1024)
    files = {"file": ("large.txt", file_content, "text/plain")}

    response = await client.post(
        f"/project/{test_project.id}/document", 
        files=files, 
        headers=auth_headers
    )

    assert response.status_code == 413
    assert "exceeds project document limit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_project_documents_list(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession):
    doc = Document(
        id=uuid4(),
        project_id=test_project.id,
        name="existing_doc.pdf",
        s3_key="some/s3/key",
        size_bytes=1024,
        content_type="application/pdf",
        uploaded_by=test_project.owner_id
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(f"/project/{test_project.id}/documents", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_download_document_presigned_url(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession, mock_s3_and_mail: dict):
    doc = Document(
        id=uuid4(),
        project_id=test_project.id,
        name="existing_doc.pdf",
        s3_key="some/s3/key",
        size_bytes=1024,
        content_type="application/pdf",
        uploaded_by=test_project.owner_id
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.get(f"/document/{doc.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["download_url"] == "https://mocked-s3-presigned-url.com/file"


@pytest.mark.asyncio
async def test_delete_document_success(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession, mock_s3_and_mail: dict):
    doc = Document(
        id=uuid4(),
        project_id=test_project.id,
        name="existing_doc.pdf",
        s3_key="some/s3/key",
        size_bytes=1024,
        content_type="application/pdf",
        uploaded_by=test_project.owner_id
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.delete(f"/document/{doc.id}", headers=auth_headers)
    assert response.status_code == 204
    assert mock_s3_and_mail["delete_file"].called


@pytest.mark.asyncio
async def test_update_document_success(client: AsyncClient, auth_headers: dict, test_project: Project, db_session: AsyncSession):
    doc = Document(
        id=uuid4(),
        project_id=test_project.id,
        name="old_name.pdf",
        s3_key="some/s3/key",
        size_bytes=1024,
        content_type="application/pdf",
        uploaded_by=test_project.owner_id
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.put(f"/document/{doc.id}", json={"name": "new_name.pdf"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "new_name.pdf"