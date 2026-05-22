from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Jobs

router = APIRouter(tags=["jobs"])


class JobBase(BaseModel):
    label: str = Field(..., min_length=1, description="岗位名称")
    description: str = Field(default="", description="岗位描述")


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, description="岗位名称")
    description: Optional[str] = Field(default=None, description="岗位描述")


class JobItem(BaseModel):
    id: int
    label: str
    description: str


class JobListResponse(BaseModel):
    success: bool = True
    items: list[JobItem]
    total: int


class JobDetailResponse(BaseModel):
    success: bool = True
    item: JobItem


class JobMutationResponse(BaseModel):
    success: bool = True
    message: str
    item: JobItem


def _serialize_job(job: Jobs) -> JobItem:
    return JobItem(
        id=job.id,
        label=job.label or "",
        description=job.description or "",
    )


def _model_dump(model: BaseModel, **kwargs):
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


def _get_job_or_404(db: Session, job_id: int) -> Jobs:
    job = db.query(Jobs).filter(Jobs.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    keyword: Optional[str] = Query(default=None, description="按岗位名称搜索"),
    db: Session = Depends(get_db),
):
    query = db.query(Jobs)
    if keyword:
        query = query.filter(Jobs.label.contains(keyword))

    jobs = query.order_by(Jobs.id.asc()).all()
    items = [_serialize_job(job) for job in jobs]
    return JobListResponse(items=items, total=len(items))


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    return JobDetailResponse(item=_serialize_job(job))


@router.post("/jobs", response_model=JobMutationResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    normalized_label = payload.label.strip()
    normalized_description = payload.description.strip()
    if not normalized_label:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job label cannot be empty",
        )

    existing_job = db.query(Jobs).filter(Jobs.label == normalized_label).first()
    if existing_job is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job label already exists",
        )

    job = Jobs(label=normalized_label, description=normalized_description)
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobMutationResponse(message="Job created", item=_serialize_job(job))


@router.put("/jobs/{job_id}", response_model=JobMutationResponse)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)

    update_data = _model_dump(payload, exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    if "label" in update_data:
        if update_data["label"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job label cannot be null",
            )

        normalized_label = update_data["label"].strip()
        if not normalized_label:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job label cannot be empty",
            )

        duplicated_job = (
            db.query(Jobs)
            .filter(Jobs.label == normalized_label, Jobs.id != job_id)
            .first()
        )
        if duplicated_job is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job label already exists",
            )
        job.label = normalized_label

    if "description" in update_data:
        description = update_data["description"]
        job.description = description.strip() if isinstance(description, str) else ""

    db.commit()
    db.refresh(job)

    return JobMutationResponse(message="Job updated", item=_serialize_job(job))


@router.delete("/jobs/{job_id}", response_model=JobMutationResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    item = _serialize_job(job)

    db.delete(job)
    db.commit()

    return JobMutationResponse(message="Job deleted", item=item)
