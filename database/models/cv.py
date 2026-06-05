from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.main import Base


class Cvs(Base):
    __tablename__ = "cvs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    filename: Mapped[str | None] = mapped_column(String)
    job_id: Mapped[str | None] = mapped_column(String, index=True)
    job_name: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)
    md5: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str | None] = mapped_column(String)
    processing_stage: Mapped[str | None] = mapped_column(String)
    processing_attempt: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String)
    ocr_engine: Mapped[str | None] = mapped_column(String)
    resume_text: Mapped[str | None] = mapped_column(String)
    resume_text_length: Mapped[int | None] = mapped_column(Integer)
    job_text: Mapped[str | None] = mapped_column(String)
    job_text_length: Mapped[int | None] = mapped_column(Integer)
    resume_summary: Mapped[str | None] = mapped_column(String)
    verify_result: Mapped[str | None] = mapped_column(String)
    score_result: Mapped[str | None] = mapped_column(String)
    interview_result: Mapped[str | None] = mapped_column(String)
    starred: Mapped[str | None] = mapped_column(String)
    final_answer: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[str | None] = mapped_column(String)


