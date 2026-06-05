from typing import Any

from database.models.cv import Cvs
from api.utils.legacy_adapter import build_cv_result_data, json_loads


def cv_item_dict(
    cv: Cvs,
    *,
    status_override: str | None = None,
    updated_at_override: str | None = None,
    error_override: str | None = None,
) -> dict[str, Any]:
    item = {
        "id": cv.id,
        "filename": cv.filename or "",
        "job_id": cv.job_id or "",
        "job_name": cv.job_name or "",
        "file_path": cv.file_path or "",
        "md5": cv.md5 or cv.id,
        "status": status_override or cv.status or "queued",
        "processing_stage": cv.processing_stage or None,
        "processing_attempt": cv.processing_attempt,
        "error": error_override if error_override is not None else (cv.error or None),
        "ocr_engine": cv.ocr_engine or None,
        "resume_text": cv.resume_text or None,
        "resume_text_length": cv.resume_text_length,
        "job_text": cv.job_text or None,
        "job_text_length": cv.job_text_length,
        "resume_summary": json_loads(cv.resume_summary),
        "verify_result": json_loads(cv.verify_result),
        "score_result": json_loads(cv.score_result),
        "interview_result": json_loads(cv.interview_result),
        "starred": str(cv.starred or "false").lower() == "true",
        "final_answer": cv.final_answer or None,
        "created_at": cv.created_at or "",
        "updated_at": updated_at_override or cv.updated_at or cv.created_at or "",
    }
    item["data"] = build_cv_result_data(item)
    return item
