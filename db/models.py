from sqlalchemy import Integer, String, inspect, text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base, engine


class Jobs(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)


# Cvs 表保存上传简历的全生命周期数据：
# 原文件信息、OCR 文本、岗位文本、结构化摘要、核验结果、评分结果和最终结论都放在这里。
class Cvs(Base):
    __tablename__ = "cvs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    filename: Mapped[str | None] = mapped_column(String)
    job_id: Mapped[str | None] = mapped_column(String, index=True)
    job_name: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)
    md5: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(String)
    ocr_engine: Mapped[str | None] = mapped_column(String)
    resume_text: Mapped[str | None] = mapped_column(String)
    resume_text_length: Mapped[int | None] = mapped_column(Integer)
    job_text: Mapped[str | None] = mapped_column(String)
    job_text_length: Mapped[int | None] = mapped_column(Integer)
    resume_summary: Mapped[str | None] = mapped_column(String)
    verify_result: Mapped[str | None] = mapped_column(String)
    score_result: Mapped[str | None] = mapped_column(String)
    final_answer: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[str | None] = mapped_column(String)


def _ensure_cvs_schema() -> None:
    """
    启动时检查 cvs 表结构是否与当前代码一致。

    当前策略比较直接：
    - 如果字段集合不一致，就重建一张新表并迁移旧数据
    - 这样可以避免 SQLite 下逐列 ALTER 的兼容问题
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "cvs" not in table_names:
        Base.metadata.create_all(bind=engine)
        return

    columns = {column["name"]: column for column in inspector.get_columns("cvs")}
    expected_columns = {
        "id",
        "filename",
        "job_id",
        "job_name",
        "file_path",
        "md5",
        "status",
        "error",
        "ocr_engine",
        "resume_text",
        "resume_text_length",
        "job_text",
        "job_text_length",
        "resume_summary",
        "verify_result",
        "score_result",
        "final_answer",
        "created_at",
        "updated_at",
    }
    current_columns = set(columns)
    id_type = str(columns.get("id", {}).get("type", "")).upper()
    needs_migration = current_columns != expected_columns or "INT" in id_type

    if not needs_migration:
        Base.metadata.create_all(bind=engine)
        return

    with engine.begin() as conn:
        # SQLite 对复杂 schema 变更支持有限，因此采用“建新表 -> 拷贝数据 -> 替换旧表”的方式迁移。
        conn.execute(text("DROP TABLE IF EXISTS cvs__new"))
        conn.execute(
            text(
                """
                CREATE TABLE cvs__new (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    filename VARCHAR,
                    job_id VARCHAR,
                    job_name VARCHAR,
                    file_path VARCHAR,
                    md5 VARCHAR,
                    status VARCHAR,
                    error VARCHAR,
                    ocr_engine VARCHAR,
                    resume_text VARCHAR,
                    resume_text_length INTEGER,
                    job_text VARCHAR,
                    job_text_length INTEGER,
                    resume_summary VARCHAR,
                    verify_result VARCHAR,
                    score_result VARCHAR,
                    final_answer VARCHAR,
                    created_at VARCHAR,
                    updated_at VARCHAR
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO cvs__new (
                    id,
                    filename,
                    job_id,
                    job_name,
                    file_path,
                    md5,
                    status,
                    error,
                    ocr_engine,
                    resume_text,
                    resume_text_length,
                    job_text,
                    job_text_length,
                    resume_summary,
                    verify_result,
                    score_result,
                    final_answer,
                    created_at,
                    updated_at
                )
                SELECT
                    CAST(id AS VARCHAR),
                    filename,
                    job_id,
                    job_name,
                    '',
                    NULL,
                    status,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    created_at,
                    created_at
                FROM cvs
                """
            )
        )
        conn.execute(text("DROP TABLE cvs"))
        conn.execute(text("ALTER TABLE cvs__new RENAME TO cvs"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cvs_id ON cvs (id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cvs_job_id ON cvs (job_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cvs_md5 ON cvs (md5)"))

    Base.metadata.create_all(bind=engine)


Base.metadata.create_all(bind=engine)
_ensure_cvs_schema()
