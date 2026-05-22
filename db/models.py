from sqlalchemy import Column, Integer, String, inspect, text

from db.database import Base, engine


class Jobs(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    description = Column(String)


class Cvs(Base):
    __tablename__ = "cvs"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    job_id = Column(String, index=True)
    job_name = Column(String)
    file_path = Column(String)
    md5 = Column(String, index=True)
    status = Column(String)
    error = Column(String)
    ocr_engine = Column(String)
    resume_text = Column(String)
    resume_text_length = Column(Integer)
    created_at = Column(String)
    updated_at = Column(String)


def _ensure_cvs_schema() -> None:
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
