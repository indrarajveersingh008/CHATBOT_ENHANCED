import re
import uuid

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def is_image_file(filename: str | None, content_type: str | None) -> bool:
    if content_type and content_type.startswith("image/"):
        return True
    ext = _file_extension(filename)
    return ext in IMAGE_EXTENSIONS


def guess_image_mime_type(filename: str | None, content_type: str | None) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type
    ext = _file_extension(filename)
    return EXT_TO_MIME.get(ext, "image/jpeg")


def normalize_content_type(filename: str | None, content_type: str | None) -> str | None:
    if content_type and content_type != "application/octet-stream":
        return content_type
    ext = _file_extension(filename)
    return EXT_TO_MIME.get(ext, content_type)


def _file_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def safe_filename(filename: str) -> str:
    """
    Turn an arbitrary uploaded filename into something safe to store on disk:
    strips any path components, replaces unsafe characters, and prefixes a
    short random id so two uploads with the same name never collide.
    """
    base = (filename or "file").replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", base) or "file"
    unique_prefix = uuid.uuid4().hex[:8]
    return f"{unique_prefix}_{base}"
