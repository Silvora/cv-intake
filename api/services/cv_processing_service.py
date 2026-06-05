from __future__ import annotations

from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from database.main import SessionLocal
from api.utils.cv_file_store import now_iso, public_file_abs_path
from api.utils.cv_repository import CvUpdatePayload, update_cv_record
from utils.log import log
from api.utils.pdf_text import extract_pdf_text
from utils.sse_conn import conn
from workflow.run import stream_cv_workflow
from workflow.state import CVState


async def publish_result(item: dict) -> None:
    await conn.publish("results", {item["id"]: item})


async def update_stage(
    db: Session,
    cv_id: str,
    *,
    status_value: str,
    processing_stage: str,
    processing_attempt: int | None = None,
    error: str | None = None,
    **kwargs,
) -> dict:
    item = update_cv_record(
        db,
        cv_id,
        CvUpdatePayload(
            status_value=status_value,
            processing_stage=processing_stage,
            processing_attempt=processing_attempt,
            error=error,
            **kwargs,
        ),
        updated_at=now_iso(),
    )
    await publish_result(item)
    return item


async def publish_workflow_stage_update(
    db: Session,
    cv_id: str,
    current_item: dict,
    *,
    processing_stage: str,
    processing_attempt: int | None = None,
    payload: dict | None = None,
) -> dict:
    next_item = update_cv_record(
        db,
        cv_id,
        CvUpdatePayload(
            status_value="processing",
            processing_stage=processing_stage,
            processing_attempt=processing_attempt,
            error=current_item.get("error"),
            ocr_engine=current_item.get("ocr_engine"),
            resume_text=current_item.get("resume_text"),
            resume_text_length=current_item.get("resume_text_length"),
            job_text=current_item.get("job_text"),
            job_text_length=current_item.get("job_text_length"),
            resume_summary=payload.get("resume_summary") if payload and "resume_summary" in payload else current_item.get("resume_summary"),
            verify_result=payload.get("verify_result") if payload and "verify_result" in payload else current_item.get("verify_result"),
            score_result=payload.get("score_result") if payload and "score_result" in payload else current_item.get("score_result"),
            interview_result=payload.get("interview_result") if payload and "interview_result" in payload else current_item.get("interview_result"),
            final_answer=payload.get("final_answer") if payload and "final_answer" in payload else current_item.get("final_answer"),
        ),
        updated_at=now_iso(),
    )
    await publish_result(next_item)
    return next_item


def derive_workflow_status(workflow_result: CVState) -> str:
    if workflow_result.get("resume_summary"):
        return "processed"
    return "error"


def derive_processing_stage(workflow_result: CVState) -> str:
    if workflow_result.get("interview_result"):
        return "interview"
    if workflow_result.get("score_result"):
        return "score"
    if workflow_result.get("verify_result"):
        return "verify"
    if workflow_result.get("resume_summary"):
        return "summary"
    return "error"


def derive_workflow_error(workflow_result: CVState) -> str | None:
    error = workflow_result.get("error")
    if isinstance(error, str) and error.strip():
        return error

    score_result = workflow_result.get("score_result") or {}
    if score_result.get("overall_status") == "blocked":
        reason = score_result.get("reason") or {}
        why_this_score = reason.get("why_this_score")
        if isinstance(why_this_score, str) and why_this_score.strip():
            return why_this_score
    return None


async def process_cv_async(cv_id: str, file_path: str, cv_name: str, job_text: str) -> None:
    db = SessionLocal()
    try:
        current_item = await update_stage(
            db,
            cv_id,
            status_value="processing",
            processing_stage="ocr",
            processing_attempt=1,
            error=None,
            job_text=job_text,
            job_text_length=len(job_text),
        )

        resume_text, engine_name = await run_in_threadpool(
            extract_pdf_text,
            public_file_abs_path(Path(file_path).name),
        )
        text_length = len(resume_text.strip())

        if text_length <= 0:
            await update_stage(
                db,
                cv_id,
                status_value="ocr_no_text",
                processing_stage="ocr_no_text",
                processing_attempt=1,
                error="PDF 文本提取结果为空",
                ocr_engine=engine_name,
                resume_text="",
                resume_text_length=0,
                job_text=job_text,
                job_text_length=len(job_text),
            )
            return

        current_item = await update_stage(
            db,
            cv_id,
            status_value="processing",
            processing_stage="summary",
            processing_attempt=1,
            error=None,
            ocr_engine=engine_name,
            resume_text=resume_text,
            resume_text_length=text_length,
            job_text=job_text,
            job_text_length=len(job_text),
        )

        log.info(
            "Start workflow: cv_id=%s, resume_text_length=%s, job_text_length=%s",
            cv_id,
            text_length,
            len(job_text),
        )
        workflow_result: CVState = {}
        stage_attempts: dict[str, int] = {}
        for update in stream_cv_workflow(cv_id, cv_name, resume_text, job_text):
            if not isinstance(update, dict):
                continue

            for node_name, payload in update.items():
                if not isinstance(payload, dict):
                    continue
                workflow_result.update(payload)
                stage = str(payload.get("processing_stage") or node_name).strip() or node_name
                stage_attempts[stage] = stage_attempts.get(stage, 0) + 1
                current_item = await publish_workflow_stage_update(
                    db,
                    cv_id,
                    current_item,
                    processing_stage=stage,
                    processing_attempt=stage_attempts[stage],
                    payload=payload,
                )

        log.info(
            "Workflow finished: cv_id=%s, has_resume_summary=%s, has_verify_result=%s, has_score_result=%s, has_interview_result=%s, error=%s",
            cv_id,
            bool(workflow_result.get("resume_summary")),
            bool(workflow_result.get("verify_result")),
            bool(workflow_result.get("score_result")),
            bool(workflow_result.get("interview_result")),
            workflow_result.get("error"),
        )
        final_stage = derive_processing_stage(workflow_result)
        await update_stage(
            db,
            cv_id,
            status_value=derive_workflow_status(workflow_result),
            processing_stage=final_stage,
            processing_attempt=stage_attempts.get(final_stage, 1),
            error=derive_workflow_error(workflow_result),
            ocr_engine=engine_name,
            resume_text=resume_text,
            resume_text_length=text_length,
            job_text=job_text,
            job_text_length=len(job_text),
            resume_summary=workflow_result.get("resume_summary"),
            verify_result=workflow_result.get("verify_result"),
            score_result=workflow_result.get("score_result"),
            interview_result=workflow_result.get("interview_result"),
            final_answer=workflow_result.get("final_answer"),
        )
    except Exception as exc:
        log.exception("Async CV process failed: cv_id=%s, error=%s", cv_id, exc)
        await update_stage(
            db,
            cv_id,
            status_value="error",
            processing_stage="error",
            processing_attempt=1,
            error=f"PDF 文本提取失败: {exc}",
            job_text=job_text,
            job_text_length=len(job_text),
        )
    finally:
        db.close()
