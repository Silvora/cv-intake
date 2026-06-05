from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database.models.cv import Cvs
from database.models.job import Jobs
from api.utils.cv_serializer import cv_item_dict
from api.utils.legacy_adapter import json_dumps


class _UnsetValue:
    pass


UNSET = _UnsetValue()


@dataclass(slots=True)
class CvUpdatePayload:
    status_value: str
    processing_stage: str | _UnsetValue = UNSET
    processing_attempt: int | None | _UnsetValue = UNSET
    error: str | None = None
    ocr_engine: str | None = None
    resume_text: str | None = None
    resume_text_length: int | None = None
    job_text: str | None | _UnsetValue = UNSET
    job_text_length: int | None | _UnsetValue = UNSET
    resume_summary: Any | _UnsetValue = UNSET
    verify_result: Any | _UnsetValue = UNSET
    score_result: Any | _UnsetValue = UNSET
    interview_result: Any | _UnsetValue = UNSET
    starred: bool | _UnsetValue = UNSET
    final_answer: str | None | _UnsetValue = UNSET


def get_cv_or_404(db: Session, cv_id: str) -> Cvs:
    cv = db.query(Cvs).filter(Cvs.id == cv_id).first()
    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {cv_id} not found",
        )
    return cv


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


def find_existing_cv_by_job_and_md5(db: Session, job_id: str, md5: str) -> Cvs | None:
    return (
        db.query(Cvs)
        .filter(Cvs.job_id == str(job_id), Cvs.md5 == md5)
        .first()
    )


def create_cv_record(
    db: Session,
    *,
    id: str,
    filename: str,
    job: Jobs,
    file_path: str,
    md5: str,
    created_at: str,
) -> dict[str, Any]:
    cv = Cvs(
        id=id,
        filename=filename,
        job_id=str(job.id),
        job_name=job.label or "",
        file_path=file_path,
        md5=md5,
        status="queued",
        processing_stage="queued",
        processing_attempt=0,
        error=None,
        ocr_engine=None,
        resume_text=None,
        resume_text_length=None,
        job_text=None,
        job_text_length=None,
        resume_summary=None,
        verify_result=None,
        score_result=None,
        interview_result=None,
        starred="false",
        final_answer=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv)


def reset_cv_for_retry(
    db: Session,
    cv: Cvs,
    *,
    filename: str,
    job: Jobs,
    file_path: str,
    md5: str,
    updated_at: str,
) -> dict[str, Any]:
    cv.filename = filename
    cv.job_id = str(job.id)
    cv.job_name = job.label or ""
    cv.file_path = file_path
    cv.md5 = md5
    cv.status = "queued"
    cv.processing_stage = "queued"
    cv.processing_attempt = 0
    cv.error = None
    cv.ocr_engine = None
    cv.resume_text = None
    cv.resume_text_length = None
    cv.job_text = None
    cv.job_text_length = None
    cv.resume_summary = None
    cv.verify_result = None
    cv.score_result = None
    cv.interview_result = None
    cv.starred = cv.starred or "false"
    cv.final_answer = None
    cv.updated_at = updated_at
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv, status_override="queued")


def update_cv_record(
    db: Session,
    cv_id: str,
    payload: CvUpdatePayload,
    *,
    updated_at: str,
) -> dict[str, Any]:
    cv = get_cv_or_404(db, cv_id)

    cv.status = payload.status_value
    if not isinstance(payload.processing_stage, _UnsetValue):
        cv.processing_stage = payload.processing_stage
    if not isinstance(payload.processing_attempt, _UnsetValue):
        cv.processing_attempt = payload.processing_attempt
    cv.error = payload.error
    if payload.ocr_engine is not None:
        cv.ocr_engine = payload.ocr_engine
    if payload.resume_text is not None or payload.status_value in {"ocr_no_text"}:
        cv.resume_text = payload.resume_text
    if payload.resume_text_length is not None or payload.status_value in {"processed", "ocr_no_text"}:
        cv.resume_text_length = payload.resume_text_length
    if not isinstance(payload.job_text, _UnsetValue):
        cv.job_text = payload.job_text
    if not isinstance(payload.job_text_length, _UnsetValue):
        cv.job_text_length = payload.job_text_length
    if not isinstance(payload.resume_summary, _UnsetValue):
        cv.resume_summary = json_dumps(payload.resume_summary)
    if not isinstance(payload.verify_result, _UnsetValue):
        cv.verify_result = json_dumps(payload.verify_result)
    if not isinstance(payload.score_result, _UnsetValue):
        cv.score_result = json_dumps(payload.score_result)
    if not isinstance(payload.interview_result, _UnsetValue):
        cv.interview_result = json_dumps(payload.interview_result)
    if not isinstance(payload.starred, _UnsetValue):
        cv.starred = "true" if payload.starred else "false"
    if not isinstance(payload.final_answer, _UnsetValue):
        cv.final_answer = payload.final_answer

    cv.updated_at = updated_at
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv)
