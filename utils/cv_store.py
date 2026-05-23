from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.models import Cvs, Jobs
from utils.log import log

ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT_DIR / "public"
CV_PUBLIC_DIR = PUBLIC_DIR / "cvs"


class _UnsetValue:
    """区分“未传值”和“显式传 None”的专用 sentinel 类型。"""


# _UNSET 用来区分“调用方没有传这个字段”和“调用方明确要写入 None”。
_UNSET = _UnsetValue()


def now_iso() -> str:
    """统一生成 UTC 时间字符串，格式为 YYYY-MM-DD HH:MM:SS。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_public_dir() -> None:
    """确保 public/cvs 目录存在。"""
    CV_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str | None) -> str:
    """去掉路径信息，防止上传文件名污染本地存储路径。"""
    candidate = Path(filename or "").name.strip()
    return candidate or "unnamed.pdf"


def hash_bytes(content: bytes) -> str:
    """对文件内容做 md5，作为内容级去重依据。"""
    return hashlib.md5(content).hexdigest()


def temp_hash(*parts: str) -> str:
    """生成临时 id，适合非持久成功记录，例如空文件或非 PDF。"""
    text = ":".join(parts)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def public_file_url(filename: str) -> str:
    """把存储文件名转换成前端可访问的相对 URL。"""
    return f"/public/cvs/{filename}"


def public_file_abs_path(filename: str) -> Path:
    """把存储文件名转换成服务器本地绝对路径。"""
    return CV_PUBLIC_DIR / filename


def _json_dumps(value: Any) -> str | None:
    """把结构化 workflow 结果序列化成 JSON 文本存入 SQLite。"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None) -> Any:
    """从 SQLite 中恢复 workflow 结果；反序列化失败时安全返回 None。"""
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _build_period(start_date: str | None, end_date: str | None) -> str | None:
    """把起止日期拼成前端更容易展示的期间字符串。"""
    if start_date and end_date:
        return f"{start_date} - {end_date}"
    return start_date or end_date or None


def _build_cv_result_data(item: dict[str, Any]) -> dict[str, Any] | None:
    """
    给前端保留一层兼容结构，避免 workflow 新字段接入后前端完全失效。

    当前前端还在消费较早期的 `data.result` 结构，这里把新的
    resume_summary / score_result 重新映射成旧结构，作为过渡层。
    """
    resume_summary = item.get("resume_summary") or {}
    score_result = item.get("score_result") or {}
    if not resume_summary and not score_result and not item.get("error"):
        return None

    user = resume_summary.get("user") or {}
    education = resume_summary.get("education") or []
    work_experiences = resume_summary.get("work_experiences") or []
    skills = resume_summary.get("skills") or []
    awards = resume_summary.get("awards") or []
    others = resume_summary.get("others") or []

    certificates = [
        other.get("name")
        for other in others
        if "证书" in str(other.get("category") or "") and other.get("name")
    ]
    languages = [
        other.get("name")
        for other in others
        if "语言" in str(other.get("category") or "") and other.get("name")
    ]
    bonus_items = [
        award.get("name")
        for award in awards
        if award.get("name")
    ] + [
        other.get("name")
        for other in others
        if other.get("name")
        and "证书" not in str(other.get("category") or "")
        and "语言" not in str(other.get("category") or "")
    ]

    result_payload = {
        "info": {
            "name": user.get("name"),
            "phone": user.get("phone"),
            "email": user.get("email"),
            "github_url": user.get("github"),
            "location": user.get("location"),
            "summary": user.get("summary"),
            "schools": [
                {
                    "school_name": entry.get("school"),
                    "degree": entry.get("degree"),
                    "study_period": _build_period(entry.get("start_date"), entry.get("end_date")),
                }
                for entry in education
            ],
        },
        "experience": {
            "experience_summary": user.get("current_job_title") or user.get("summary"),
            "work_experiences": [
                {
                    "company": entry.get("company"),
                    "duration": _build_period(entry.get("start_date"), entry.get("end_date")),
                    "projects": [entry.get("description")] if entry.get("description") else [],
                }
                for entry in work_experiences
            ],
        },
        "skill": {
            "skills": [skill.get("name") for skill in skills if skill.get("name")],
            "bonus_items": [value for value in bonus_items if value],
            "certificates": [value for value in certificates if value],
            "languages": [value for value in languages if value],
        },
        "score": {
            "score": score_result.get("score"),
            "reason": score_result.get("reason"),
            "improvement_suggestions": score_result.get("improvement_suggestions") or [],
        },
        "meta": {
            "generated_at": score_result.get("generated_at"),
        },
    }
    error_payload = None
    if item.get("error"):
        error_payload = {
            "code": item.get("status"),
            "message": item.get("error"),
            "ocr_engine": item.get("ocr_engine"),
        }
    return {
        "result": result_payload,
        "error": error_payload,
    }


def cv_item_dict(
    cv: Cvs,
    *,
    status_override: str | None = None,
    updated_at_override: str | None = None,
    error_override: str | None = None,
) -> dict[str, Any]:
    """
    把 ORM 模型统一转换成 API/SSE 可直接返回的字典。

    这里同时负责：
    - 反序列化 workflow JSON 字段
    - 生成过渡期的 data.result 结构
    """
    item = {
        "id": cv.id,
        "filename": cv.filename or "",
        "job_id": cv.job_id or "",
        "job_name": cv.job_name or "",
        "file_path": cv.file_path or "",
        "md5": cv.md5 or cv.id,
        "status": status_override or cv.status or "queued",
        "error": error_override if error_override is not None else (cv.error or None),
        "ocr_engine": cv.ocr_engine or None,
        "resume_text": cv.resume_text or None,
        "resume_text_length": cv.resume_text_length,
        "job_text": cv.job_text or None,
        "job_text_length": cv.job_text_length,
        "resume_summary": _json_loads(cv.resume_summary),
        "verify_result": _json_loads(cv.verify_result),
        "score_result": _json_loads(cv.score_result),
        "final_answer": cv.final_answer or None,
        "created_at": cv.created_at or "",
        "updated_at": updated_at_override or cv.updated_at or cv.created_at or "",
    }
    item["data"] = _build_cv_result_data(item)
    return item


def get_job_or_404(db: Session, job_id: str) -> Jobs:
    """按字符串 job_id 查询岗位，不存在时抛出标准 HTTP 错误。"""
    normalized_job_id = str(job_id).strip()
    if not normalized_job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_id is required",
        )

    if not normalized_job_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_id must be numeric",
        )

    job = db.query(Jobs).filter(Jobs.id == int(normalized_job_id)).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {normalized_job_id} not found",
        )
    return job


async def save_uploaded_cv(
    *,
    file: UploadFile,
    job: Jobs,
    db: Session,
) -> tuple[dict[str, Any], bool]:
    """
    保存上传的简历文件，并创建或复用一条 cvs 记录。

    返回值：
    - dict[str, Any]: 当前简历记录的可序列化结果
    - bool: 是否接受进入后续 OCR / workflow 处理
    """
    created_at = now_iso()
    original_filename = sanitize_filename(file.filename)
    ext = Path(original_filename).suffix.lower()
    content = await file.read()

    is_pdf = ext == ".pdf" or file.content_type in {
        "application/pdf",
        "application/x-pdf",
    }

    if not is_pdf:
        skipped_id = temp_hash(str(job.id), original_filename, created_at, "non-pdf")
        return {
            "id": skipped_id,
            "filename": original_filename,
            "job_id": str(job.id),
            "job_name": job.label or "",
            "file_path": "",
            "md5": skipped_id,
            "status": "skipped_non_pdf",
            "error": "Only PDF files are supported",
            "created_at": created_at,
            "updated_at": created_at,
        }, False

    if not content:
        skipped_id = temp_hash(str(job.id), original_filename, created_at, "empty")
        return {
            "id": skipped_id,
            "filename": original_filename,
            "job_id": str(job.id),
            "job_name": job.label or "",
            "file_path": "",
            "md5": skipped_id,
            "status": "skipped_empty_file",
            "error": "Empty file is not supported",
            "created_at": created_at,
            "updated_at": created_at,
        }, False

    # 同一份 PDF 在不同岗位下应保留独立记录，因此：
    # - md5 仍表示“文件内容 hash”
    # - cv_id 改成 job_id + md5 的组合 hash
    content_hash = hash_bytes(content)
    cv_id = temp_hash(str(job.id), content_hash)
    storage_ext = ext or ".pdf"
    storage_name = f"{cv_id}{storage_ext}"
    file_url = public_file_url(storage_name)

    existing = (
        db.query(Cvs)
        .filter(Cvs.job_id == str(job.id), Cvs.md5 == content_hash)
        .first()
    )
    if existing is not None:
        # 只对“同岗位 + 同文件内容”做去重。
        if existing.status == "processed":
            log.info(
                "Skip duplicate processed CV in same job: job_id=%s, hash=%s, filename=%s, existing_status=%s",
                job.id,
                content_hash,
                original_filename,
                existing.status,
            )
            return cv_item_dict(
                existing,
                status_override="skipped_duplicate_md5",
                updated_at_override=created_at,
                error_override="Duplicate file",
            ), False

        log.info(
            "Reuse existing CV for retry: job_id=%s, hash=%s, filename=%s, existing_status=%s",
            job.id,
            content_hash,
            original_filename,
            existing.status,
        )
        existing.filename = original_filename
        existing.job_id = str(job.id)
        existing.job_name = job.label or ""
        existing.file_path = file_url
        existing.md5 = content_hash
        existing.status = "queued"
        existing.error = None
        existing.ocr_engine = None
        existing.resume_text = None
        existing.resume_text_length = None
        existing.job_text = None
        existing.job_text_length = None
        existing.resume_summary = None
        existing.verify_result = None
        existing.score_result = None
        existing.final_answer = None
        # 复用旧记录时清空 workflow 结果，保证这次重新处理不会读到脏数据。
        existing.updated_at = created_at
        db.commit()
        db.refresh(existing)
        return cv_item_dict(
            existing,
            status_override="queued",
        ), True

    ensure_public_dir()
    storage_path = CV_PUBLIC_DIR / storage_name
    storage_path.write_bytes(content)
    log.info(
        "Stored uploaded CV: cv_id=%s, hash=%s, filename=%s, path=%s",
        cv_id,
        content_hash,
        original_filename,
        storage_path,
    )

    cv = Cvs(
        id=cv_id,
        filename=original_filename,
        job_id=str(job.id),
        job_name=job.label or "",
        file_path=file_url,
        md5=content_hash,
        status="queued",
        error=None,
        ocr_engine=None,
        resume_text=None,
        resume_text_length=None,
        job_text=None,
        job_text_length=None,
        resume_summary=None,
        verify_result=None,
        score_result=None,
        final_answer=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv), True


def update_cv_status(
    db: Session,
    cv_id: str,
    *,
    status_value: str,
    error: str | None = None,
    ocr_engine: str | None = None,
    resume_text: str | None = None,
    resume_text_length: int | None = None,
    job_text: str | None | _UnsetValue = _UNSET,
    job_text_length: int | None | _UnsetValue = _UNSET,
    resume_summary: Any | _UnsetValue = _UNSET,
    verify_result: Any | _UnsetValue = _UNSET,
    score_result: Any | _UnsetValue = _UNSET,
    final_answer: str | None | _UnsetValue = _UNSET,
) -> dict[str, Any]:
    """
    统一更新 cvs 表中的阶段状态和 workflow 结果。

    这个函数是上传链路里最核心的持久化入口：
    OCR、workflow、错误兜底都通过这里写库。
    """
    cv = db.query(Cvs).filter(Cvs.id == cv_id).first()
    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {cv_id} not found",
        )

    cv.status = status_value
    cv.error = error
    if ocr_engine is not None:
        cv.ocr_engine = ocr_engine
    if resume_text is not None or status_value in {"ocr_no_text"}:
        cv.resume_text = resume_text
    if resume_text_length is not None or status_value in {"processed", "ocr_no_text"}:
        cv.resume_text_length = resume_text_length
    if not isinstance(job_text, _UnsetValue):
        cv.job_text = job_text
    if not isinstance(job_text_length, _UnsetValue):
        cv.job_text_length = job_text_length
    if not isinstance(resume_summary, _UnsetValue):
        cv.resume_summary = _json_dumps(resume_summary)
    if not isinstance(verify_result, _UnsetValue):
        cv.verify_result = _json_dumps(verify_result)
    if not isinstance(score_result, _UnsetValue):
        cv.score_result = _json_dumps(score_result)
    if not isinstance(final_answer, _UnsetValue):
        cv.final_answer = final_answer
    cv.updated_at = now_iso()
    db.commit()
    db.refresh(cv)
    return cv_item_dict(cv)


def delete_cv_file(file_path: str | None) -> None:
    if not file_path:
        return

    normalized = file_path.lstrip("/\\")
    absolute_path = (ROOT_DIR / normalized).resolve()
    public_root = PUBLIC_DIR.resolve()

    if public_root == absolute_path or public_root in absolute_path.parents:
        absolute_path.unlink(missing_ok=True)
