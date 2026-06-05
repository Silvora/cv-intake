from langchain_openai import ChatOpenAI

from config.app import appConfig
from database.main import SessionLocal
from database.models.settings import Settings


def get_llm() -> ChatOpenAI:
    try:
        db = SessionLocal()
        try:
            settings = db.query(Settings).filter(Settings.id == 1).first()
        finally:
            db.close()

        if settings is not None:
            return ChatOpenAI(
                model=settings.model,
                temperature=settings.temperature,
                api_key=settings.api_key,
                base_url=settings.base_url,
            )
    except Exception:
        pass

    return ChatOpenAI(
        model=appConfig.llm.model,
        temperature=appConfig.llm.temperature,
        api_key=appConfig.llm.api_key,
        base_url=appConfig.llm.base_url,
    )


llm = get_llm()
