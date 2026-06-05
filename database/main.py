from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(__file__).resolve().parent / "app.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"

# connect_args 是 SQLite 专有参数，设置为 False 以允许多线程访问，解决 FastAPI 中的并发问题[reference:3]
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base with proper static typing support."""
    pass


class DataBase:
    def __init__(self) -> None:
        self.db_path = DB_PATH
        self.engine = engine
        self.alembic_ini_path = ALEMBIC_INI_PATH

    def init(self) -> None:
        # python -m alembic revision --autogenerate -m "add remark to cvs"
        # python -m alembic upgrade head

        # 延迟导入，确保所有模型在 create_all 前完成注册。
        from database.models.cv import Cvs
        from database.models.job import Jobs
        from database.models.settings import Settings

        _ = (Cvs, Jobs, Settings)
        config = Config(str(self.alembic_ini_path))

        if not self.db_path.exists():
            Base.metadata.create_all(bind=self.engine)
            command.stamp(config, "head")
            return

        inspector = inspect(self.engine)
        table_names = set(inspector.get_table_names())

        if "alembic_version" not in table_names:
            command.stamp(config, "head")
            return

        command.upgrade(config, "head")



def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
