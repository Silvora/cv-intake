import json
from typing import Any


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def build_period(start_date: str | None, end_date: str | None) -> str | None:
    if start_date and end_date:
        return f"{start_date} - {end_date}"
    return start_date or end_date or None


def build_cv_result_data(item: dict[str, Any]) -> dict[str, Any] | None:
    resume_summary = item.get("resume_summary") or {}
    score_result = item.get("score_result") or {}
    interview_result = item.get("interview_result") or {}
    if not resume_summary and not score_result and not interview_result and not item.get("error"):
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
                    "study_period": build_period(entry.get("start_date"), entry.get("end_date")),
                }
                for entry in education
            ],
        },
        "experience": {
            "experience_summary": user.get("current_job_title") or user.get("summary"),
            "work_experiences": [
                {
                    "company": entry.get("company"),
                    "duration": build_period(entry.get("start_date"), entry.get("end_date")),
                    "projects": [
                        value
                        for value in [entry.get("project_name"), entry.get("description")]
                        if value
                    ],
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
        "interview": interview_result,
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
