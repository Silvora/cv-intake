from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CvBase(BaseModel):
    filename: str
    job_id: str
    job_name: str = ""
    file_path: str = ""
    md5: str | None = None
    status: str = "queued"
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
    starred: bool = False
    final_answer: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CvCreate(CvBase):
    id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)


class CvUpdate(BaseModel):
    filename: str | None = Field(default=None, min_length=1)
    job_id: str | None = Field(default=None, min_length=1)
    job_name: str | None = None
    file_path: str | None = None
    md5: str | None = None
    status: str | None = Field(default=None, min_length=1)
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
    starred: bool | None = None
    final_answer: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CvItem(CvBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class CvListResponse(BaseModel):
    success: bool = True
    items: list[CvItem]
    total: int


class CvDetailResponse(BaseModel):
    success: bool = True
    item: CvItem


class CvMutationResponse(BaseModel):
    success: bool = True
    message: str
    item: CvItem

