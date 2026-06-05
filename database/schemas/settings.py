from pydantic import BaseModel, ConfigDict, Field


class SettingBase(BaseModel):
    model: str
    temperature: float = 0.7
    api_key: str
    base_url: str
    zhipu_search_api_key: str
    created_at: str | None = None
    updated_at: str | None = None


class SettingCreate(SettingBase):
    model: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    zhipu_search_api_key: str = Field(..., min_length=1)


class SettingUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    temperature: float | None = None
    api_key: str | None = Field(default=None, min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    zhipu_search_api_key: str | None = Field(default=None, min_length=1)
    created_at: str | None = None
    updated_at: str | None = None


class SettingItem(SettingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SettingResponse(BaseModel):
    success: bool = True
    item: SettingItem


class SettingMutationResponse(BaseModel):
    success: bool = True
    message: str
    item: SettingItem
