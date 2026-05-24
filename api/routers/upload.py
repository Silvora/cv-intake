import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import SessionLocal, get_db
from utils.cv_store import (
    get_job_or_404,
    public_file_abs_path,
    save_uploaded_cv,
    update_cv_status,
)
from utils.log import log
from utils.pdf_text import extract_pdf_text
from utils.sse_conn import conn
from workflow.run import run_cv_workflow
from workflow.state import State

# 上传路由是整个“PDF -> OCR -> Workflow -> DB -> SSE”链路的入口。
# 这里不做复杂业务判断，核心职责是编排步骤并持续把阶段结果写回数据库和 SSE。
router = APIRouter(tags=["upload"])


class UploadItem(BaseModel):
    # 这个模型描述上传接口和 SSE 推送给前端的单条简历记录结构。
    # 字段既包含 OCR 中间态，也包含 workflow 最终产物，方便前端逐步刷新显示。
    id: str
    filename: str
    job_id: str
    job_name: str = ""
    file_path: str = ""
    md5: str | None = None
    status: str
    error: str | None = None
    ocr_engine: str | None = None
    resume_text: str | None = None
    resume_text_length: int | None = None
    job_text: str | None = None
    job_text_length: int | None = None
    resume_summary: dict | None = None
    verify_result: dict | None = None
    score_result: dict | None = None
    final_answer: str | None = None
    data: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UploadResponse(BaseModel):
    success: bool = True
    message: str
    count: int
    items: list[UploadItem]


async def _publish_result(item: dict) -> None:
    """把单条简历最新状态推送到 SSE，前端会按 id 合并状态。"""
    await conn.publish("results", {item["id"]: item})


async def _process_cv_async(cv_id: str, file_path: str, job_text: str) -> None:
    """
    后台异步处理单份简历。

    这个任务只负责 OCR + workflow + 最终结果落库，
    不阻塞上传 HTTP 请求。
    """
    db = SessionLocal()
    try:
        extracting_item = update_cv_status(
            db,
            cv_id,
            status_value="processing",
            error=None,
            job_text=job_text,
            job_text_length=len(job_text),
        )
        await _publish_result(extracting_item)

        resume_text, engine_name = await run_in_threadpool(
            extract_pdf_text,
            public_file_abs_path(Path(file_path).name),
        )
        text_length = len(resume_text.strip())

        if text_length <= 0:
            processed_item = update_cv_status(
                db,
                cv_id,
                status_value="ocr_no_text",
                error="PDF 文本提取结果为空",
                ocr_engine=engine_name,
                resume_text="",
                resume_text_length=0,
                job_text=job_text,
                job_text_length=len(job_text),
            )
            await _publish_result(processed_item)
            return

        extracted_item = update_cv_status(
            db,
            cv_id,
            status_value="processing",
            error=None,
            ocr_engine=engine_name,
            resume_text=resume_text,
            resume_text_length=text_length,
            job_text=job_text,
            job_text_length=len(job_text),
        )
        await _publish_result(extracted_item)

        workflow_result = await run_in_threadpool(
            run_cv_workflow,
            resume_text,
            job_text,
        )
        processed_item = update_cv_status(
            db,
            cv_id,
            status_value=_derive_workflow_status(workflow_result),
            error=_derive_workflow_error(workflow_result),
            ocr_engine=engine_name,
            resume_text=resume_text,
            resume_text_length=text_length,
            job_text=job_text,
            job_text_length=len(job_text),
            resume_summary=workflow_result.get("resume_summary"),
            verify_result=workflow_result.get("verify_result"),
            score_result=workflow_result.get("score_result"),
            final_answer=workflow_result.get("final_answer"),
        )
        await _publish_result(processed_item)
    except Exception as exc:
        log.exception("Async CV process failed: cv_id=%s, error=%s", cv_id, exc)
        processed_item = update_cv_status(
            db,
            cv_id,
            status_value="error",
            error=f"PDF 文本提取失败: {exc}",
            job_text=job_text,
            job_text_length=len(job_text),
        )
        await _publish_result(processed_item)
    finally:
        db.close()


def _derive_workflow_status(workflow_result: State) -> str:
    """
    根据 workflow 的最终 state 推导数据库 status。

    当前约定比较保守：
    - 只要 resume_summary 已经生成，就认为主流程完成，状态记为 processed
    - 连结构化摘要都没有，则记为 error
    """
    if workflow_result.get("resume_summary"):
        return "processed"
    return "error"


def _derive_workflow_error(workflow_result: State) -> str | None:
    """
    从 workflow state 中抽取最有代表性的错误信息，落到 cvs.error。

    优先级：
    1. workflow 顶层 error
    2. score_result 中 blocked 的原因
    """
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


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: list[UploadFile] = File(...),
    job_id: str | None = Form(default=None),
    job_ids: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    上传多个 PDF，并串行完成每份简历的处理。

    整体流程：
    1. 校验 job_id，拿到岗位描述
    2. 保存 PDF 到 public 目录，并在 cvs 表插入 queued 记录
    3. 提取 PDF 文本
    4. 调用 workflow 跑 summary / verify / score
    5. 把中间态和最终结果持续写回数据库
    6. 每个阶段都通过 SSE 推送给前端
    """
    selected_job_id = (job_id or job_ids or "").strip()
    job = get_job_or_404(db, selected_job_id)
    log.info("Upload request received: job_id=%s, files=%s", selected_job_id, len(files))

    items: list[UploadItem] = []
    accepted_count = 0
    results_payload: dict[str, dict] = {}

    for file in files:
        try:
            # save_uploaded_cv 只负责落盘和保存基础信息，不在这里做 OCR / workflow。
            log.info("Start handling upload file: filename=%s", file.filename)
            item, accepted = await save_uploaded_cv(file=file, job=job, db=db)
            items.append(UploadItem(**item))

            results_payload[item["id"]] = item
            if accepted:
                accepted_count += 1
                asyncio.create_task(
                    _process_cv_async(
                        item["id"],
                        item["file_path"],
                        job.description or "",
                    )
                )
            log.info(
                "Upload file handled: filename=%s, hash=%s, status=%s, accepted=%s",
                file.filename,
                item["id"],
                item["status"],
                accepted,
            )
        finally:
            await file.close()

    if results_payload:
        await conn.publish("results", results_payload)

    final_items: list[UploadItem] = []
    for item in items:
        if item.status != "queued":
            final_items.append(item)
            continue
        final_items.append(item)

    return UploadResponse(
        message="Upload completed",
        count=accepted_count,
        items=final_items,
    )
