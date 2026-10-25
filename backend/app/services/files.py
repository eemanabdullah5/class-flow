"""Saving and deleting uploaded submission files safely.

Rules:
- Only PDF, DOCX, ZIP, PNG and JPG, checked by extension AND by the file's first bytes
  (its "signature"), so a renamed program can't pass as homework.
- At most 10 MB.
- Saved under a random name. The student's filename is only kept for display.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.models import MAX_UPLOAD_BYTES

CHUNK_BYTES = 1024 * 1024  # read 1 MB at a time

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# extension -> (content type we send back on download, accepted first bytes)
ALLOWED_FILES = {
    ".pdf": ("application/pdf", (b"%PDF-",)),
    ".docx": (DOCX_TYPE, (b"PK\x03\x04",)),  # a .docx is a ZIP inside
    ".zip": ("application/zip", (b"PK\x03\x04", b"PK\x05\x06")),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
}
ALLOWED_LIST = "PDF, DOCX, ZIP, PNG or JPG"


class UploadRejected(Exception):
    """The file broke one of the rules. status_code says which HTTP error to send."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class SavedFile:
    stored_filename: str
    original_filename: str
    content_type: str
    file_size: int


def upload_dir() -> Path:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings.upload_dir


def stored_path(stored_filename: str) -> Path:
    return upload_dir() / stored_filename


def display_name(filename: str | None) -> str:
    """Keep only the last part of the name, so "../../evil.pdf" becomes "evil.pdf"."""
    name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    return name[-255:] or "file"


def save_upload(upload: UploadFile) -> SavedFile:
    original = display_name(upload.filename)
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_FILES:
        raise UploadRejected(f"File type not allowed. Please upload a {ALLOWED_LIST} file.", 415)
    content_type, signatures = ALLOWED_FILES[extension]

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    destination = stored_path(stored_filename)
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := upload.file.read(CHUNK_BYTES):
                if size == 0 and not chunk.startswith(signatures):
                    raise UploadRejected(
                        f"This file's contents don't match a real {extension} file.", 415
                    )
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise UploadRejected("File is too large. The limit is 10 MB.", 413)
                out.write(chunk)
        if size == 0:
            raise UploadRejected("The file is empty.", 422)
    except BaseException:
        destination.unlink(missing_ok=True)  # never leave half-saved files behind
        raise

    return SavedFile(stored_filename, original, content_type, size)


def delete_file(stored_filename: str) -> None:
    stored_path(stored_filename).unlink(missing_ok=True)
