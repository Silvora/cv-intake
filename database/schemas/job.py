from pydantic import BaseModel, ConfigDict, Field


NonEmptyText = Field(..., min_length=1)


class JobBase(BaseModel):
    label: str
    description: str = ""


class JobCreate(JobBase):
    label: str = NonEmptyText


class JobUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    description: str | None = None


class JobItem(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


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
