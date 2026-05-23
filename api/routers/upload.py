from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
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
            # save_uploaded_cv 会完成去重、落盘和 DB 初始记录写入。
            log.info("Start handling upload file: filename=%s", file.filename)
            item, accepted = await save_uploaded_cv(file=file, job=job, db=db)
            items.append(UploadItem(**item))

            results_payload[item["id"]] = item
            if accepted:
                accepted_count += 1
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
            # 跳过非 queued 的记录，例如非 PDF、空文件、同岗位重复文件。
            final_items.append(item)
            continue

        job_text = (job.description or "").strip()
        job_text_length = len(job_text)
        # 进入 processing，表示文件已经入库，开始做 OCR 和工作流处理。
        extracting_item = update_cv_status(
            db,
            item.id,
            status_value="processing",
            error=None,
            job_text=job_text,
            job_text_length=job_text_length,
        )
        log.info("Start PDF extract: cv_id=%s, filename=%s", item.id, item.filename)
        await _publish_result(extracting_item)

        try:
            file_path = public_file_abs_path(Path(item.file_path).name)
            resume_text, engine_name = extract_pdf_text(file_path)
            text_length = len(resume_text.strip())

            if text_length > 0:
                # OCR 成功后先保存原始文本，再继续跑 workflow。
                extracted_item = update_cv_status(
                    db,
                    item.id,
                    status_value="processing",
                    error=None,
                    ocr_engine=engine_name,
                    resume_text=resume_text,
                    resume_text_length=text_length,
                    job_text=job_text,
                    job_text_length=job_text_length,
                )
                await _publish_result(extracted_item)

                # workflow 调用可能阻塞，因此放到线程池中执行，避免卡住事件循环。
                workflow_result = await run_in_threadpool(
                    run_cv_workflow,
                    resume_text,
                    job_text,
                )
                # 把结构化摘要、核验结果、评分结果和最终结论一次性落库。
                processed_item = update_cv_status(
                    db,
                    item.id,
                    status_value=_derive_workflow_status(workflow_result),
                    error=_derive_workflow_error(workflow_result),
                    ocr_engine=engine_name,
                    resume_text=resume_text,
                    resume_text_length=text_length,
                    job_text=job_text,
                    job_text_length=job_text_length,
                    resume_summary=workflow_result.get("resume_summary"),
                    verify_result=workflow_result.get("verify_result"),
                    score_result=workflow_result.get("score_result"),
                    final_answer=workflow_result.get("final_answer"),
                )
                log.info(
                    "Workflow finished: cv_id=%s, status=%s, engine=%s, text_length=%s",
                    item.id,
                    processed_item["status"],
                    engine_name,
                    text_length,
                )
            else:
                # OCR 成功执行但没有文本时，不进入 workflow，直接标记为 ocr_no_text。
                processed_item = update_cv_status(
                    db,
                    item.id,
                    status_value="ocr_no_text",
                    error="PDF 文本提取结果为空",
                    ocr_engine=engine_name,
                    resume_text="",
                    resume_text_length=0,
                    job_text=job_text,
                    job_text_length=job_text_length,
                )
                log.warning(
                    "PDF extract empty: cv_id=%s, engine=%s",
                    item.id,
                    engine_name,
                )
        except Exception as exc:
            # 这里兜底 OCR 和 workflow 编排阶段的异常，避免单份简历打断整个上传请求。
            log.exception("PDF extract failed: cv_id=%s, filename=%s, error=%s", item.id, item.filename, exc)
            processed_item = update_cv_status(
                db,
                item.id,
                status_value="error",
                error=f"PDF 文本提取失败: {exc}",
                ocr_engine="pypdf/pdfplumber",
                job_text=job_text,
                job_text_length=job_text_length,
            )

        # 无论成功失败，都推送最终状态并放入响应。
        await _publish_result(processed_item)
        final_items.append(UploadItem(**processed_item))

    return UploadResponse(
        message="Upload completed",
        count=accepted_count,
        items=final_items,
    )
