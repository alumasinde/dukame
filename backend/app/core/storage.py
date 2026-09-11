from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

_IMAGE_TYPES: dict[str, tuple[str, bytes]] = {
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/gif": ("gif", b"GIF"),
}


def _safe_segment(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", value) or "unknown"


def _validate_image_header(content_type: str, header: bytes) -> str:
    if content_type == "image/webp":
        valid = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
        if not valid:
            raise HTTPException(
                status_code=415,
                detail="The uploaded file is not a valid WebP image",
            )
        return "webp"

    image_type = _IMAGE_TYPES.get(content_type)
    if image_type is None:
        raise HTTPException(
            status_code=415,
            detail="Only JPEG, PNG, GIF, and WebP images are supported",
        )

    extension, signature = image_type
    if not header.startswith(signature):
        raise HTTPException(
            status_code=415,
            detail="The uploaded file does not match its image type",
        )
    return extension


async def save_product_image(
    file: UploadFile,
    tenant_public_id: str,
    product_public_id: str,
) -> str:
    content_type = (file.content_type or "").lower()
    header = await file.read(32)
    extension = _validate_image_header(content_type, header)

    root = Path(settings.media_root).resolve()
    directory = (
        root
        / "products"
        / _safe_segment(tenant_public_id)
        / _safe_segment(product_public_id)
    )
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{extension}"
    destination = directory / filename
    temporary = directory / f".{filename}.uploading"
    size = len(header)

    try:
        with temporary.open("wb") as output:
            output.write(header)
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.media_max_bytes:
                    raise HTTPException(status_code=413, detail="Image is too large")
                output.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return (
        f"/uploads/products/{_safe_segment(tenant_public_id)}"
        f"/{_safe_segment(product_public_id)}/{filename}"
    )


def delete_local_media(url: str) -> None:
    prefix = "/uploads/"
    if not url.startswith(prefix):
        return

    root = Path(settings.media_root).resolve()
    relative = Path(url.removeprefix(prefix))
    target = (root / relative).resolve()
    if root not in target.parents:
        return
    target.unlink(missing_ok=True)
