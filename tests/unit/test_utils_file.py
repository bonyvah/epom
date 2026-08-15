import pytest

from app.utils.file import validate_and_infer_mime


def test_validate_and_infer_mime_pdf():
    # PDF magic bytes: %PDF-
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n..."
    mime = validate_and_infer_mime("report.pdf", pdf_bytes)
    assert mime == "application/pdf"


def test_validate_and_infer_mime_png():
    # PNG magic bytes: \x89PNG\r\n\x1a\n
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
    mime = validate_and_infer_mime("image.png", png_bytes)
    assert mime == "image/png"


def test_validate_and_infer_mime_txt():
    # UTF-8 text file
    text_bytes = b"This is a simple text file."
    mime = validate_and_infer_mime("readme.txt", text_bytes)
    assert mime == "text/plain"


def test_validate_and_infer_mime_unsupported_extension():
    # UTF-8 code but extension is not .txt
    text_bytes = b"print('hello')"
    with pytest.raises(ValueError) as exc_info:
        validate_and_infer_mime("script.py", text_bytes)
    assert "Unsupported file type" in str(exc_info.value)


def test_validate_and_infer_mime_invalid_binary():
    # Random non-UTF-8 binary data
    invalid_bytes = b"\xff\xfe\x00\xff\x00\xff"
    with pytest.raises(ValueError) as exc_info:
        validate_and_infer_mime("random.bin", invalid_bytes)
    assert "Unsupported file type" in str(exc_info.value)