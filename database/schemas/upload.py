from typing import Any

from pydantic import BaseModel


class UploadItem(BaseModel):
    id: str
    filename: str
    job_id: str
    job_name: str = ""
    file_path: str = ""
    md5: str | None = None
    status: str
    processing_stage: str | None = None
    processing_attempt: int | None = None
    error: str | None = None
    ocr_engine: str | None = None
    resume_text: str | None = None
    resume_text_length: int | None = None
    job_text: str | None = None
    job_text_length: int | None = None
    resume_summary: dict[str, Any] | None = None
    verify_result: dict[str, Any] | None = None
    score_result: dict[str, Any] | None = None
    interview_result: dict[str, Any] | None = None
    final_answer: str | None = None
    data: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UploadResponse(BaseModel):
    success: bool = True
    message: str
    count: int
    items: list[UploadItem]
