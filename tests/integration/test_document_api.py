import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.models import Project, Document

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
    assert "id" in data
    
    assert mock_s3_and_mail["upload_file"].called


@pytest.mark.asyncio
async def test_get_project_documents_list(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project,
    db_session: AsyncSession
):
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

    response = await client.get(
        f"/project/{test_project.id}/documents", 
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "existing_doc.pdf"


@pytest.mark.asyncio
async def test_download_document_presigned_url(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project,
    db_session: AsyncSession,
    mock_s3_and_mail: dict
):
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

    response = await client.get(
        f"/document/{doc.id}", 
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
    assert data["download_url"] == "https://mocked-s3-presigned-url.com/file"
    assert mock_s3_and_mail["generate_presigned_url"].called