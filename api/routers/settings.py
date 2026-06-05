from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.main import get_db
from database.models.settings import Settings
from database.schemas.settings import (
    SettingItem,
    SettingMutationResponse,
    SettingResponse,
    SettingUpdate,
)
from api.utils.cv_file_store import now_iso

router = APIRouter(tags=["settings"])


def _build_default_setting_item() -> SettingItem:
    return SettingItem(
        id=1,
        model="",
        temperature=0.7,
        api_key="",
        base_url="",
        zhipu_search_api_key="",
        created_at=None,
        updated_at=None,
    )


def _ensure_settings_row(db: Session) -> Settings:
    item = db.query(Settings).filter(Settings.id == 1).first()
    if item is not None:
        return item

    item = Settings(
        id=1,
        model="",
        temperature=0.7,
        api_key="",
        base_url="",
        zhipu_search_api_key="",
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/settings", response_model=SettingResponse)
def get_settings(db: Session = Depends(get_db)):
    item = db.query(Settings).filter(Settings.id == 1).first()
    if item is None:
        return SettingResponse(item=_build_default_setting_item())
    return SettingResponse(item=SettingItem.model_validate(item))


@router.put("/settings", response_model=SettingMutationResponse)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db)):
    item = _ensure_settings_row(db)

    normalized_model = (payload.model or "").strip()
    normalized_api_key = (payload.api_key or "").strip()
    normalized_base_url = (payload.base_url or "").strip()
    normalized_zhipu_api_key = (payload.zhipu_search_api_key or "").strip()

    if not normalized_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model cannot be empty",
        )
    if not normalized_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key cannot be empty",
        )
    if not normalized_base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url cannot be empty",
        )
    if not normalized_zhipu_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zhipu_search_api_key cannot be empty",
        )

    item.model = normalized_model
    item.temperature = float(payload.temperature or 0.7)
    item.api_key = normalized_api_key
    item.base_url = normalized_base_url
    item.zhipu_search_api_key = normalized_zhipu_api_key
    if not item.created_at:
        item.created_at = now_iso()
    item.updated_at = now_iso()

    db.commit()
    db.refresh(item)

    return SettingMutationResponse(
        message="Settings updated",
        item=SettingItem.model_validate(item),
    )
