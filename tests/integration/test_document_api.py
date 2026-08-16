from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Project


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


@pytest.mark.asyncio
async def test_unauthorized_document_access(client: AsyncClient, test_project: Project, db_session: AsyncSession):
    # 1. Create a document in test_project
    doc = Document(
        id=uuid4(),
        project_id=test_project.id,
        name="secret.pdf",
        s3_key="some/secret/key",
        size_bytes=1024,
        content_type="application/pdf",
        uploaded_by=test_project.owner_id
    )
    db_session.add(doc)
    await db_session.commit()

    # 2. Create another user (not a member of test_project)
    from app.models import User
    from app.utils.auth import hash_password, create_access_token
    unauth_user = User(username="unauth@example.com", hashed_password=hash_password("password"))
    db_session.add(unauth_user)
    await db_session.commit()

    unauth_token = create_access_token(str(unauth_user.id))
    unauth_headers = {"Authorization": f"Bearer {unauth_token}"}

    # 3. Attempt download
    res = await client.get(f"/document/{doc.id}", headers=unauth_headers)
    assert res.status_code == 404

    # 4. Attempt update
    res = await client.put(f"/document/{doc.id}", json={"name": "hacked.pdf"}, headers=unauth_headers)
    assert res.status_code == 404

    # 5. Attempt delete
    res = await client.delete(f"/document/{doc.id}", headers=unauth_headers)
    assert res.status_code == 404

    # 6. Attempt upload to this project
    files = {"file": ("unauth.txt", b"some bytes", "text/plain")}
    res = await client.post(f"/project/{test_project.id}/document", files=files, headers=unauth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_upload_document_s3_failure(client: AsyncClient, auth_headers: dict, test_project: Project):
    from unittest.mock import patch
    with patch("app.services.document.upload_file", side_effect=Exception("S3 error")):
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        res = await client.post(
            f"/project/{test_project.id}/document", 
            files=files, 
            headers=auth_headers
        )
        assert res.status_code == 503
        assert res.json()["detail"] == "Failed to upload file"


@pytest.mark.asyncio
async def test_upload_document_db_failure_cleanup(
    client: AsyncClient, 
    auth_headers: dict, 
    test_project: Project, 
    mock_s3_and_mail: dict
):
    from unittest.mock import patch
    # Mock db commit to fail during upload
    with patch("app.services.document.AsyncSession.commit", side_effect=Exception("DB error")):
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        with pytest.raises(Exception, match="DB error"):
            await client.post(
                f"/project/{test_project.id}/document", 
                files=files, 
                headers=auth_headers
            )
        
        # Verify that delete_file was called on the mock to cleanup the S3 object
        assert mock_s3_and_mail["delete_file"].called