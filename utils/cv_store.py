from datetime import datetime, timezone
import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.models import Cvs, Jobs
from utils.log import log

ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT_DIR / "public"
CV_PUBLIC_DIR = PUBLIC_DIR / "cvs"


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


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


def cv_item_dict(
    cv: Cvs,
    *,
    status_override: str | None = None,
    updated_at_override: str | None = None,
    error_override: str | None = None,
) -> dict:
    return {
        "id": cv.id,
        "filename": cv.filename or "",
        "job_id": cv.job_id or "",
        "job_name": cv.job_name or "",
        "file_path": cv.file_path or "",
        "md5": cv.md5 or cv.id,
        "status": status_override or cv.status or "queued",
        "error": error_override if error_override is not None else (cv.error or None),
        "ocr_engine": cv.ocr_engine or None,
        "resume_text": cv.resume_text or None,
        "resume_text_length": cv.resume_text_length,
        "created_at": cv.created_at or "",
        "updated_at": updated_at_override or cv.updated_at or cv.created_at or "",
    }


def get_job_or_404(db: Session, job_id: str) -> Jobs:
    normalized_job_id = str(job_id).strip()
    if not normalized_job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_id is required",
        )

    if not normalized_job_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_id must be numeric",
        )

    job = db.query(Jobs).filter(Jobs.id == int(normalized_job_id)).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {normalized_job_id} not found",
        )
    return job


async def save_uploaded_cv(
    *,
    file: UploadFile,
    job: Jobs,
    db: Session,
) -> tuple[dict, bool]:
    created_at = now_iso()
    original_filename = sanitize_filename(file.filename)
    ext = Path(original_filename).suffix.lower()
    content = await file.read()

    is_pdf = ext == ".pdf" or file.content_type in {
        "application/pdf",
        "application/x-pdf",
    }

    if not is_pdf:
        skipped_id = temp_hash(str(job.id), original_filename, created_at, "non-pdf")
        return {
            "id": skipped_id,
            "filename": original_filename,
            "job_id": str(job.id),
            "job_name": job.label or "",
            "file_path": "",
            "md5": skipped_id,
            "status": "skipped_non_pdf",
            "error": "Only PDF files are supported",
            "created_at": created_at,
            "updated_at": created_at,
        }, False

    if not content:
        skipped_id = temp_hash(str(job.id), original_filename, created_at, "empty")
        return {
            "id": skipped_id,
            "filename": original_filename,
            "job_id": str(job.id),
            "job_name": job.label or "",
            "file_path": "",
            "md5": skipped_id,
            "status": "skipped_empty_file",
            "error": "Empty file is not supported",
            "created_at": created_at,
            "updated_at": created_at,
        }, False

    cv_id = hash_bytes(content)
    storage_ext = ext or ".pdf"
    storage_name = f"{cv_id}{storage_ext}"
    file_url = public_file_url(storage_name)

    existing = db.query(Cvs).filter(Cvs.id == cv_id).first()
    if existing is not None:
        if existing.status == "processed":
            log.info(
                "Skip duplicate processed CV: hash=%s, filename=%s, existing_status=%s",
                cv_id,
                original_filename,
                existing.status,
            )
            return cv_item_dict(
                existing,
                status_override="skipped_duplicate_md5",
                updated_at_override=created_at,
                error_override="Duplicate file",
            ), False

        log.info(
            "Reuse existing CV for retry: hash=%s, filename=%s, existing_status=%s",
            cv_id,
            original_filename,
            existing.status,
        )
        existing.filename = original_filename
        existing.job_id = str(job.id)
        existing.job_name = job.label or ""
        existing.file_path = file_url
        existing.md5 = cv_id
        existing.status = "queued"
        existing.error = None
        existing.ocr_engine = None
        existing.resume_text = None
        existing.resume_text_length = None
        existing.updated_at = created_at
        db.commit()
        db.refresh(existing)
        return cv_item_dict(
            existing,
            status_override="queued",
        ), True

    ensure_public_dir()
    storage_path = CV_PUBLIC_DIR / storage_name
    storage_path.write_bytes(content)
    log.info(
        "Stored uploaded CV: hash=%s, filename=%s, path=%s",
        cv_id,
        original_filename,
        storage_path,
    )

    cv = Cvs(
        id=cv_id,
        filename=original_filename,
        job_id=str(job.id),
        job_name=job.label or "",
        file_path=file_url,
        md5=cv_id,
        status="queued",
        error=None,
        ocr_engine=None,
        resume_text=None,
        resume_text_length=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv), True


def update_cv_status(
    db: Session,
    cv_id: str,
    *,
    status_value: str,
    error: str | None = None,
    ocr_engine: str | None = None,
    resume_text: str | None = None,
    resume_text_length: int | None = None,
) -> dict:
    cv = db.query(Cvs).filter(Cvs.id == cv_id).first()
    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {cv_id} not found",
        )

    cv.status = status_value
    cv.error = error
    if ocr_engine is not None:
        cv.ocr_engine = ocr_engine
    if resume_text is not None or status_value in {"ocr_no_text"}:
        cv.resume_text = resume_text
    if resume_text_length is not None or status_value in {"processed", "ocr_no_text"}:
        cv.resume_text_length = resume_text_length
    cv.updated_at = now_iso()
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv)


def delete_cv_file(file_path: str | None) -> None:
    if not file_path:
        return

    normalized = file_path.lstrip("/\\")
    absolute_path = (ROOT_DIR / normalized).resolve()
    public_root = PUBLIC_DIR.resolve()

    if public_root == absolute_path or public_root in absolute_path.parents:
        absolute_path.unlink(missing_ok=True)
