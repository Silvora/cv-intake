"""initial schema

Revision ID: 0.0.5
Revises: None
Create Date: 2026-06-05 11:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0.0.5"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
    )
    op.create_index("ix_jobs_id", "jobs", ["id"], unique=False)

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("api_key", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("zhipu_search_api_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_index("ix_settings_id", "settings", ["id"], unique=False)

    op.create_table(
        "cvs",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("job_name", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("md5", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("processing_stage", sa.String(), nullable=True),
        sa.Column("processing_attempt", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("ocr_engine", sa.String(), nullable=True),
        sa.Column("resume_text", sa.String(), nullable=True),
        sa.Column("resume_text_length", sa.Integer(), nullable=True),
        sa.Column("job_text", sa.String(), nullable=True),
        sa.Column("job_text_length", sa.Integer(), nullable=True),
        sa.Column("resume_summary", sa.String(), nullable=True),
        sa.Column("verify_result", sa.String(), nullable=True),
        sa.Column("score_result", sa.String(), nullable=True),
        sa.Column("interview_result", sa.String(), nullable=True),
        sa.Column("starred", sa.String(), nullable=True),
        sa.Column("final_answer", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_index("ix_cvs_id", "cvs", ["id"], unique=False)
    op.create_index("ix_cvs_job_id", "cvs", ["job_id"], unique=False)
    op.create_index("ix_cvs_md5", "cvs", ["md5"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cvs_md5", table_name="cvs")
    op.drop_index("ix_cvs_job_id", table_name="cvs")
    op.drop_index("ix_cvs_id", table_name="cvs")
    op.drop_table("cvs")

    op.drop_index("ix_settings_id", table_name="settings")
    op.drop_table("settings")

    op.drop_index("ix_jobs_id", table_name="jobs")
    op.drop_table("jobs")
