import filetype

ALLOWED_MIMES = {
    "application/pdf",  # .pdf
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "image/jpeg",  # .jpg / .jpeg
    "image/png",  # .png
    "image/gif",  # .gif
}


def validate_and_infer_mime(filename: str, contents: bytes) -> str:
    kind = filetype.guess(contents[:2048])

    if kind is not None:
        if kind.mime in ALLOWED_MIMES:
            return kind.mime
    else:
        try:
            contents[:2048].decode("utf-8")
            if filename.endswith(".txt"):
                return "text/plain"
        except UnicodeDecodeError:
            pass

    raise ValueError(
        "Unsupported file type. Allowed formats: PDF, DOCX, XLSX, TXT, JPG, JPEG, PNG, GIF."
    )
