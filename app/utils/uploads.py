"""Save stall and court logos under static/uploads. The original filename is not kept."""

import secrets
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


class UploadError(Exception):
    pass


def save_image(file_storage) -> str | None:
    """Store an uploaded image and return its static-relative path."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return None
    original = secure_filename(file_storage.filename)
    extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise UploadError("Use a png, jpg, or webp image.")
    # Random name so one upload cannot overwrite another file.
    filename = f"{secrets.token_hex(8)}.{extension}"
    folder = Path(current_app.static_folder) / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    file_storage.save(folder / filename)
    return f"uploads/{filename}"
