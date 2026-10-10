"""Validate and privately store uploaded documents without processing their contents."""

from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage


ALLOWED_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


class DocumentValidationError(ValueError):
    """An uploaded file does not meet the supported document constraints."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def store_document(uploaded_file: FileStorage, upload_directory: str | Path, max_size: int):
    filename = Path((uploaded_file.filename or "").replace("\\", "/")).name.strip()
    if not filename:
        raise DocumentValidationError("Choose a file with a valid filename.", "invalid_filename")
    if len(filename) > 255 or any(ord(character) < 32 for character in filename):
        raise DocumentValidationError(
            "Choose a filename with 255 characters or fewer.",
            "invalid_filename",
        )

    extension = Path(filename).suffix.lower()
    signatures = ALLOWED_SIGNATURES.get(extension)
    if signatures is None:
        raise DocumentValidationError(
            "Only PDF, PNG, JPG, and JPEG files are supported.",
            "unsupported_type",
        )

    content = uploaded_file.stream.read(max_size + 1)
    if len(content) > max_size:
        raise DocumentValidationError("The file exceeds the 10 MB upload limit.", "too_large")
    if not content:
        raise DocumentValidationError("The selected file is empty.", "empty_file")
    if not any(content.startswith(signature) for signature in signatures):
        raise DocumentValidationError(
            "The file contents do not match the selected PDF, PNG, or JPEG file type.",
            "invalid_contents",
        )

    destination = Path(upload_directory)
    destination.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    destination_file = destination / stored_name
    try:
        with destination_file.open("xb") as stored_file:
            stored_file.write(content)
    except OSError:
        destination_file.unlink(missing_ok=True)
        raise

    return {
        "filename": filename,
        "stored_filename": stored_name,
        "size": len(content),
    }