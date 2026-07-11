import re
import uuid


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
