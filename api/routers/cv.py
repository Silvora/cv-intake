from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database.main import get_db
from database.models.cv import Cvs
from database.schemas.cv import (
    CvDetailResponse,
    CvItem,
    CvListResponse,
    CvMutationResponse,
    CvUpdate,
)
from api.utils.cv_file_store import delete_cv_file, now_iso
from api.utils.cv_repository import get_cv_or_404, get_job_or_404
from api.utils.cv_serializer import cv_item_dict
from api.utils.upload_service import save_uploaded_cv
from utils.sse_conn import conn

router = APIRouter(tags=["cvs"])


def _model_dump(model, **kwargs):
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


def _to_cv_list_item(cv: Cvs) -> CvItem:
    item = cv_item_dict(cv)
    return CvItem(
        id=item["id"],
        filename=item["filename"],
        job_id=item["job_id"],
        job_name=item["job_name"],
        file_path=item["file_path"],
        md5=item["md5"],
        status=item["status"],
        processing_stage=item["processing_stage"],
        processing_attempt=item["processing_attempt"],
        error=item["error"],
        ocr_engine=item["ocr_engine"],
        resume_text_length=item["resume_text_length"],
        final_answer=item["final_answer"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        score_result=item["score_result"],
        interview_result=item["interview_result"],
        starred=item["starred"],
    )


@router.get("/cvs", response_model=CvListResponse)
def list_cvs(
    job_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Cvs)

    if job_id:
        query = query.filter(Cvs.job_id == job_id)

    if status_filter:
        query = query.filter(Cvs.status == status_filter)

    if keyword:
        query = query.filter(Cvs.filename.contains(keyword))

    items = [
        _to_cv_list_item(cv)
        for cv in query.order_by(Cvs.updated_at.desc(), Cvs.created_at.desc()).all()
    ]
    return CvListResponse(items=items, total=len(items))


@router.get("/cvs/{cv_id}", response_model=CvDetailResponse)
def get_cv(cv_id: str, db: Session = Depends(get_db)):
    cv = get_cv_or_404(db, cv_id)
    return CvDetailResponse(item=CvItem(**cv_item_dict(cv)))


@router.post("/cvs", response_model=CvMutationResponse, status_code=status.HTTP_201_CREATED)
async def create_cv(
    file: UploadFile = File(...),
    job_id: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        job = get_job_or_404(db, job_id)
        item, created = await save_uploaded_cv(file=file, job=job, db=db)
    finally:
        await file.close()

    if not created:
        current_status = item.get("status")
        await conn.publish("results", {item["id"]: item})
        if current_status == "skipped_duplicate_md5":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CV already exists",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=item.get("error") or "CV create failed",
        )

    await conn.publish("results", {item["id"]: item})
    return CvMutationResponse(message="CV created", item=CvItem(**item))


@router.put("/cvs/{cv_id}", response_model=CvMutationResponse)
async def update_cv(cv_id: str, payload: CvUpdate, db: Session = Depends(get_db)):
    cv = get_cv_or_404(db, cv_id)
    update_data = _model_dump(payload, exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    if "filename" in update_data:
        normalized_filename = (update_data["filename"] or "").strip()
        if not normalized_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="filename cannot be empty",
            )
        cv.filename = normalized_filename

    if "job_id" in update_data and update_data["job_id"] is not None:
        job = get_job_or_404(db, str(update_data["job_id"]))
        cv.job_id = str(job.id)
        cv.job_name = job.label or ""

    if "status" in update_data and update_data["status"] is not None:
        normalized_status = update_data["status"].strip()
        if not normalized_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status cannot be empty",
            )
        cv.status = normalized_status

    if "error" in update_data:
        cv.error = update_data["error"].strip() if isinstance(update_data["error"], str) else None

    if "starred" in update_data and update_data["starred"] is not None:
        cv.starred = "true" if update_data["starred"] else "false"

    cv.updated_at = now_iso()
    db.commit()
    db.refresh(cv)
    item = cv_item_dict(cv)
    await conn.publish("results", {item["id"]: item})

    return CvMutationResponse(message="CV updated", item=CvItem(**item))


@router.delete("/cvs/{cv_id}", response_model=CvMutationResponse)
async def delete_cv(cv_id: str, db: Session = Depends(get_db)):
    cv = get_cv_or_404(db, cv_id)
    item = CvItem(**cv_item_dict(cv))
    delete_cv_file(cv.file_path)
    db.delete(cv)
    db.commit()
    item_payload = item.model_dump() if hasattr(item, "model_dump") else item.dict()
    await conn.publish(
        "results",
        {
            item.id: {
                **item_payload,
                "status": "deleted",
                "updated_at": now_iso(),
            }
        },
    )
    return CvMutationResponse(message="CV deleted", item=item)
