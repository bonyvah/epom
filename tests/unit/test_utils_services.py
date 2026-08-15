import pytest
from unittest.mock import patch, MagicMock
from app.utils.s3 import upload_file, delete_file, generate_presigned_url
from app.utils.send_mail import send_mail

@pytest.mark.asyncio
async def test_s3_upload_file():
    with patch("app.utils.s3.s3") as mock_s3:
        await upload_file("test-key", b"content", "text/plain")
        mock_s3.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_s3_delete_file():
    with patch("app.utils.s3.s3") as mock_s3:
        await delete_file("test-key")
        mock_s3.delete_object.assert_called_once()


@pytest.mark.asyncio
async def test_s3_generate_presigned_url():
    with patch("app.utils.s3.s3") as mock_s3:
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"
        url = await generate_presigned_url("test-key")
        assert url == "https://presigned.url"
        mock_s3.generate_presigned_url.assert_called_once()


@pytest.mark.asyncio
async def test_send_mail_wrapper():
    with patch("resend.Emails.send") as mock_resend_send:
        await send_mail("sender@epom.com", "recipient@test.com", "Subject", "Body")
        mock_resend_send.assert_called_once_with({
            "from": "sender@epom.com",
            "to": "recipient@test.com",
            "subject": "Subject",
            "html": "Body",
        })