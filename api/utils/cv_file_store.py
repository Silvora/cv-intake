from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT_DIR / "public"
CV_PUBLIC_DIR = PUBLIC_DIR / "cvs"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_public_dir() -> None:
    CV_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str | None) -> str:
    candidate = Path(filename or "").name.strip()
    return candidate or "unnamed.pdf"


def hash_bytes(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def temp_hash(*parts: str) -> str:
    text = ":".join(parts)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def public_file_url(filename: str) -> str:
    return f"/public/cvs/{filename}"


def public_file_abs_path(filename: str) -> Path:
    return CV_PUBLIC_DIR / filename


def write_cv_file(filename: str, content: bytes) -> Path:
    ensure_public_dir()
    storage_path = CV_PUBLIC_DIR / filename
    storage_path.write_bytes(content)
    return storage_path


def delete_cv_file(file_path: str | None) -> None:
    if not file_path:
        return

    normalized = file_path.lstrip("/\\")
    absolute_path = (ROOT_DIR / normalized).resolve()
    public_root = PUBLIC_DIR.resolve()

    if public_root == absolute_path or public_root in absolute_path.parents:
        absolute_path.unlink(missing_ok=True)
