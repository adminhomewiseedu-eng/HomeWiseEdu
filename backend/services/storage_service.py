import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import settings

ALLOWED_UPLOADS = {
    ".txt": {"text/plain"},
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"},
    ".png": {"image/png"}, ".webp": {"image/webp"},
    ".mp3": {"audio/mpeg"}, ".wav": {"audio/wav", "audio/x-wav"},
    ".ogg": {"audio/ogg"}, ".webm": {"audio/webm", "video/webm"},
    ".mp4": {"video/mp4", "audio/mp4"}, ".mov": {"video/quicktime"},
}


def atomic_write_bytes(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _content_matches(extension: str, content: bytes) -> bool:
    if extension in {".jpg", ".jpeg"}: return content.startswith(b"\xff\xd8\xff")
    if extension == ".png": return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp": return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    if extension == ".pdf": return content.startswith(b"%PDF-")
    if extension == ".docx": return content.startswith(b"PK\x03\x04")
    if extension == ".wav": return content.startswith(b"RIFF") and content[8:12] == b"WAVE"
    if extension == ".mp3": return content.startswith(b"ID3") or (len(content) > 1 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0)
    if extension in {".webm"}: return content.startswith(b"\x1aE\xdf\xa3")
    if extension in {".mp4", ".mov"}: return len(content) > 12 and content[4:8] == b"ftyp"
    if extension == ".ogg": return content.startswith(b"OggS")
    if extension == ".txt":
        try:
            content.decode("utf-8")
            return b"\x00" not in content
        except UnicodeDecodeError:
            return False
    return False


async def save_evidence_upload(upload: UploadFile) -> tuple[str, str]:
    extension = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
    if extension not in ALLOWED_UPLOADS or content_type not in ALLOWED_UPLOADS[extension]:
        raise HTTPException(status_code=415, detail="Unsupported evidence file type")
    content = await upload.read(settings.MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Evidence file is empty")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Evidence file exceeds the configured size limit")
    if not _content_matches(extension, content):
        raise HTTPException(status_code=415, detail="File content does not match its declared type")
    generated_name = f"{uuid.uuid4().hex}{extension}"
    destination = Path(settings.EVIDENCE_DIR) / generated_name
    try:
        atomic_write_bytes(destination, content)
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Evidence storage is temporarily unavailable") from exc
    return f"/uploads/evidence/{generated_name}", generated_name
