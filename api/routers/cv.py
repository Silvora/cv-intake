from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Cvs
from utils.cv_store import (
    cv_item_dict,
    delete_cv_file,
    get_job_or_404,
    now_iso,
    save_uploaded_cv,
)
from utils.sse_conn import conn

router = APIRouter(tags=["cvs"])


class CvItem(BaseModel):
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


class CvListItem(BaseModel):
    id: str
    filename: str
    job_id: str
    job_name: str = ""
    file_path: str = ""
    md5: str | None = None
    status: str
    error: str | None = None
    ocr_engine: str | None = None
    resume_text_length: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CvListResponse(BaseModel):
    success: bool = True
    items: list[CvListItem]
    total: int


class CvDetailResponse(BaseModel):
    success: bool = True
    item: CvItem


class CvMutationResponse(BaseModel):
    success: bool = True
    message: str
    item: CvItem


class CvUpdate(BaseModel):
    filename: Optional[str] = Field(default=None, min_length=1)
    job_id: Optional[str] = None
    status: Optional[str] = Field(default=None, min_length=1)
    error: Optional[str] = None


def _model_dump(model: BaseModel, **kwargs):
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


def _get_cv_or_404(db: Session, cv_id: str) -> Cvs:
    cv = db.query(Cvs).filter(Cvs.id == cv_id).first()
    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {cv_id} not found",
        )
    return cv


def _to_cv_list_item(cv: Cvs) -> CvListItem:
    item = cv_item_dict(cv)
    return CvListItem(
        id=item["id"],
        filename=item["filename"],
        job_id=item["job_id"],
        job_name=item["job_name"],
        file_path=item["file_path"],
        md5=item["md5"],
        status=item["status"],
        error=item["error"],
        ocr_engine=item["ocr_engine"],
        resume_text_length=item["resume_text_length"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
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
    cv = _get_cv_or_404(db, cv_id)
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
    cv = _get_cv_or_404(db, cv_id)
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

    cv.updated_at = now_iso()
    db.commit()
    db.refresh(cv)
    item = cv_item_dict(cv)
    await conn.publish("results", {item["id"]: item})

    return CvMutationResponse(message="CV updated", item=CvItem(**item))


@router.delete("/cvs/{cv_id}", response_model=CvMutationResponse)
async def delete_cv(cv_id: str, db: Session = Depends(get_db)):
    cv = _get_cv_or_404(db, cv_id)
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
