from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from database.models.job import Jobs
from api.utils.cv_file_store import (
    hash_bytes,
    now_iso,
    public_file_url,
    sanitize_filename,
    temp_hash,
    write_cv_file,
)
from api.utils.cv_repository import (
    create_cv_record,
    find_existing_cv_by_job_and_md5,
    reset_cv_for_retry,
)
from api.utils.cv_serializer import cv_item_dict
from utils.log import log


async def save_uploaded_cv(
    *,
    file: UploadFile,
    job: Jobs,
    db: Session,
) -> tuple[dict[str, Any], bool]:
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
            "processing_stage": None,
            "processing_attempt": None,
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
            "processing_stage": None,
            "processing_attempt": None,
            "error": "Empty file is not supported",
            "created_at": created_at,
            "updated_at": created_at,
        }, False

    content_hash = hash_bytes(content)
    cv_id = temp_hash(str(job.id), content_hash)
    storage_ext = ext or ".pdf"
    storage_name = f"{cv_id}{storage_ext}"
    file_url = public_file_url(storage_name)

    existing = find_existing_cv_by_job_and_md5(db, str(job.id), content_hash)
    if existing is not None:
        if existing.status == "processed":
            log.info(
                "Skip duplicate processed CV in same job: job_id=%s, hash=%s, filename=%s, existing_status=%s",
                job.id,
                content_hash,
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
            "Reuse existing CV for retry: job_id=%s, hash=%s, filename=%s, existing_status=%s",
            job.id,
            content_hash,
            original_filename,
            existing.status,
        )
        return reset_cv_for_retry(
            db,
            existing,
            filename=original_filename,
            job=job,
            file_path=file_url,
            md5=content_hash,
            updated_at=created_at,
        ), True

    storage_path = write_cv_file(storage_name, content)
    log.info(
        "Stored uploaded CV: cv_id=%s, hash=%s, filename=%s, path=%s",
        cv_id,
        content_hash,
        original_filename,
        storage_path,
    )

    return create_cv_record(
        db,
        id=cv_id,
        filename=original_filename,
        job=job,
        file_path=file_url,
        md5=content_hash,
        created_at=created_at,
    ), True
