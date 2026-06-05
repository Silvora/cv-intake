from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api.services.worker_queue import get_cv_queue
from api.utils.cv_repository import get_job_or_404
from utils.log import log
from utils.sse_conn import conn
from api.utils.upload_service import save_uploaded_cv as save_uploaded_cv_record
from api.workers.cv_worker import process_cv_job


async def upload_files_service(
    *,
    files: list[UploadFile],
    selected_job_id: str,
    db: Session,
) -> dict[str, Any]:
    job = get_job_or_404(db, selected_job_id)
    log.info("Upload request received: job_id=%s, files=%s", selected_job_id, len(files))

    items: list[dict[str, Any]] = []
    accepted_count = 0
    results_payload: dict[str, dict] = {}

    for file in files:
        try:
            log.info("Start handling upload file: filename=%s", file.filename)
            item, accepted = await save_uploaded_cv_record(file=file, job=job, db=db)
            items.append(item)
            results_payload[item["id"]] = item

            if accepted:
                accepted_count += 1
                get_cv_queue().enqueue(
                    process_cv_job,
                    item["id"],
                    item["file_path"],
                    item["filename"],
                    job.description or "",
                )

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

    return {
        "message": "Upload completed",
        "count": accepted_count,
        "items": items,
    }
