from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from utils.cv_store import (
    get_job_or_404,
    public_file_abs_path,
    save_uploaded_cv,
    update_cv_status,
)
from utils.log import log
from utils.pdf_text import extract_pdf_text
from utils.sse_conn import conn

router = APIRouter(tags=["upload"])


class UploadItem(BaseModel):
    id: str
    filename: str
    job_id: str
    job_name: str = ""
    file_path: str = ""
    md5: str | None = None
    status: str
    error: str | None = None
    ocr_engine: str | None = None
    resume_text: str | None = None
    resume_text_length: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UploadResponse(BaseModel):
    success: bool = True
    message: str
    count: int
    items: list[UploadItem]


async def _publish_result(item: dict) -> None:
    await conn.publish("results", {item["id"]: item})


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: list[UploadFile] = File(...),
    job_id: str | None = Form(default=None),
    job_ids: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    selected_job_id = (job_id or job_ids or "").strip()
    job = get_job_or_404(db, selected_job_id)
    log.info("Upload request received: job_id=%s, files=%s", selected_job_id, len(files))

    items: list[UploadItem] = []
    accepted_count = 0
    results_payload: dict[str, dict] = {}

    for file in files:
        try:
            log.info("Start handling upload file: filename=%s", file.filename)
            item, accepted = await save_uploaded_cv(file=file, job=job, db=db)
            items.append(UploadItem(**item))

            results_payload[item["id"]] = item
            if accepted:
                accepted_count += 1
            log.info(
                "Upload file handled: filename=%s, hash=%s, status=%s, accepted=%s",
                file.filename,
                item["id"],
                item["status"],
                accepted,
            )
        finally:
            await file.close()

    if results_payload:
        await conn.publish("results", results_payload)

    final_items: list[UploadItem] = []
    for item in items:
        if item.status != "queued":
            final_items.append(item)
            continue

        extracting_item = update_cv_status(
            db,
            item.id,
            status_value="processing",
            error=None,
        )
        log.info("Start PDF extract: cv_id=%s, filename=%s", item.id, item.filename)
        await _publish_result(extracting_item)

        try:
            file_path = public_file_abs_path(f"{item.id}.pdf")
            resume_text, engine_name = extract_pdf_text(file_path)
            text_length = len(resume_text.strip())

            if text_length > 0:
                processed_item = update_cv_status(
                    db,
                    item.id,
                    status_value="processed",
                    error=None,
                    ocr_engine=engine_name,
                    resume_text=resume_text,
                    resume_text_length=text_length,
                )
                log.info(
                    "PDF extract success: cv_id=%s, engine=%s, text_length=%s",
                    item.id,
                    engine_name,
                    text_length,
                )
            else:
                processed_item = update_cv_status(
                    db,
                    item.id,
                    status_value="ocr_no_text",
                    error="PDF 文本提取结果为空",
                    ocr_engine=engine_name,
                    resume_text="",
                    resume_text_length=0,
                )
                log.warning(
                    "PDF extract empty: cv_id=%s, engine=%s",
                    item.id,
                    engine_name,
                )
        except Exception as exc:
            log.exception("PDF extract failed: cv_id=%s, filename=%s, error=%s", item.id, item.filename, exc)
            processed_item = update_cv_status(
                db,
                item.id,
                status_value="error",
                error=f"PDF 文本提取失败: {exc}",
                ocr_engine="pypdf/pdfplumber",
            )

        await _publish_result(processed_item)
        final_items.append(UploadItem(**processed_item))

    return UploadResponse(
        message="Upload completed",
        count=accepted_count,
        items=final_items,
    )
