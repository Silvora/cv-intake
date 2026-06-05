from typing import Any

from zai import ZhipuAiClient

from config.app import appConfig
from database.main import SessionLocal
from database.models.settings import Settings

ZHIPU_VERIFY_TIMEOUT_SECONDS = 60.0
ZHIPU_WEB_SEARCH_ENGINE = "search_pro"
ZHIPU_WEB_SEARCH_COUNT = 2


def get_client() -> ZhipuAiClient:
    try:
        db = SessionLocal()
        try:
            settings = db.query(Settings).filter(Settings.id == 1).first()
        finally:
            db.close()

        if settings is not None and (settings.zhipu_search_api_key or "").strip():
            return ZhipuAiClient(api_key=settings.zhipu_search_api_key.strip())
    except Exception:
        pass

    api_key = (appConfig.zhipu.api_key or "").strip()
    if not api_key:
        raise ValueError("zhipu_search_api_key is empty")
    return ZhipuAiClient(api_key=api_key)


def web_search(
    target_type: str,
    target_name: str,
    search_query: str,
) -> dict[str, Any]:
    client = get_client()
    try:
        response = client.web_search.web_search(
            search_engine=ZHIPU_WEB_SEARCH_ENGINE,
            search_query=search_query,
            count=ZHIPU_WEB_SEARCH_COUNT,
            search_recency_filter="noLimit",
            content_size="high",
            timeout=ZHIPU_VERIFY_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        return {
            "target_type": target_type,
            "target_name": target_name,
            "search_query": search_query,
            "error": str(exc),
        }

    return {
        "target_type": target_type,
        "target_name": target_name,
        "search_query": search_query,
        "response": response,
    }
