from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from database.main import get_db
from database.schemas.upload import UploadResponse
from api.services.upload_service import upload_files_service

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: list[UploadFile] = File(...),
    job_id: str | None = Form(default=None),
    job_ids: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    selected_job_id = (job_id or job_ids or "").strip()
    payload = await upload_files_service(
        files=files,
        selected_job_id=selected_job_id,
        db=db,
    )
    return UploadResponse(**payload)
