import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings

settings = get_settings()

LOGO_SUBDIR = "assets/logos"

ALLOWED_DOC_TYPES = {
    "text/plain": {".txt"},
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}

ALLOWED_IMAGE_TYPES = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/svg+xml": {".svg"},
    "image/webp": {".webp"},
}


def sanitise_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._\- ]", "_", base).strip().rstrip(".")
    return base[:120] or "file"


def stored_filename(extension: str) -> str:
    return f"{uuid.uuid4().hex}{extension}"


async def save_upload(
    org_id: int,
    subdir: str,
    file: UploadFile,
    allowed_types: dict[str, set[str]],
) -> tuple[str, str, str, int]:
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(415, f"Unsupported file type: {content_type or 'unknown'}")
    original = sanitise_filename(file.filename or "upload")
    extension = Path(original).suffix.lower()
    allowed_extensions = allowed_types[content_type]
    if not extension or extension not in allowed_extensions:
        raise HTTPException(415, "File extension is missing or does not match the declared type")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit")
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(422, "Uploaded file is empty")
    directory = Path(settings.upload_dir) / str(org_id) / subdir
    directory.mkdir(parents=True, exist_ok=True)
    stored = stored_filename(extension)
    (directory / stored).write_bytes(b"".join(chunks))
    return stored, original, content_type, total


def upload_path(org_id: int, subdir: str, stored: str) -> Path:
    return Path(settings.upload_dir) / str(org_id) / subdir / stored


def delete_upload(org_id: int, subdir: str, stored: str) -> None:
    path = upload_path(org_id, subdir, stored)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
