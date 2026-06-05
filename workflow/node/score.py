from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from workflow.llm import llm
from workflow.node.summary import ResumeSummary
from workflow.node.verify import VerifyResult
from workflow.state import CVState


# ScoreNode 只做岗位匹配评分：
# 结合 JD、简历摘要、核验风险，输出结构化分数和原因。
def _default_score_breakdown() -> "ScoreBreakdown":
    """给 Pydantic default_factory 用的零参工厂。"""
    return ScoreBreakdown.model_validate({})


def _default_score_reason() -> "ScoreReason":
    """给 Pydantic default_factory 用的零参工厂。"""
    return ScoreReason.model_validate({})


class ScoreBreakdown(BaseModel):
    """岗位匹配分项分数，统一使用 0-100 的整数。"""

    overall: int = 0
    must_have_match: int = 0
    experience_match: int = 0
    skill_match: int = 0
    education_match: int = 0


class ScoreReason(BaseModel):
    """模型给出的打分解释。"""

    why_this_score: str = ""
    met_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)


class ScoreResult(BaseModel):
    """
    ScoreNode 的统一输出结构。

    结构尽量贴近前端现有的 `score` 数据约定，避免后面再做字段转换。
    """

    overall_status: str = "scored"
    upstream_error: str | None = None
    score: ScoreBreakdown = Field(default_factory=_default_score_breakdown)
    reason: ScoreReason = Field(default_factory=_default_score_reason)
    improvement_suggestions: list[str] = Field(default_factory=list)
    generated_at: str = ""


SCORING_PROMPT = """
你是一个招聘简历评分器。你的任务是根据招聘信息和候选人的简历结构化信息，对候选人与岗位的匹配度进行打分。

请严格遵守以下规则：
1. 总分和各分项分数都必须是 0 到 100 的整数。
2. 分项包括：
   - must_have_match：岗位硬性要求匹配度
   - experience_match：工作/项目经验匹配度
   - skill_match：技能匹配度
   - education_match：教育背景匹配度
3. overall 需要综合四个分项以及核验风险来给出。
4. 如果 verify_result 中存在高风险或明显缺失，可以下调 overall，并在 risk_points 中说明。
5. 只能基于输入中的事实打分，不要臆造候选人经历或岗位要求。
6. 如果岗位描述没有明确写某类要求，例如学历要求不清晰，可以给出保守判断，但必须在 why_this_score 中说明。
7. met_requirements 写已经明确匹配到的要求。
8. missing_requirements 写简历中未体现或明显不足的要求。
9. risk_points 写抽取不确定性、核验风险、信息缺失、时间线异常等风险点。
10. improvement_suggestions 给招聘方或候选人的下一步建议，要求简洁、可执行。
11. why_this_score 用中文简洁说明为什么是这个分数，不要空话。
"""


def ScoreNode(state: CVState) -> CVState:
    """
    ScoreNode 负责基于岗位文本、简历摘要和核验结果进行最终打分。

    输入：
    - state["job_text"]：招聘信息/JD
    - state["resume_summary"]：SummaryNode 的结构化输出
    - state["verify_result"]：VerifyNode 的核验结果

    输出：
    - state["score_result"]：结构化评分结果
    - state["final_answer"]：便于直接展示的简短结论
    """

    job_text = (state.get("job_text") or "").strip()
    resume_summary_data = state.get("resume_summary") or {}
    verify_result_data = state.get("verify_result") or {}
    upstream_error = state.get("error")

    # 缺任何关键输入都直接返回 blocked，而不是让模型在脏输入上硬打分。
    if not job_text:
        result = _build_blocked_score_result(
            message="job_text is empty",
            suggestion="提供完整的招聘信息后再执行评分。",
            upstream_error=upstream_error,
        )
        return {
            "node": "end",
            "processing_stage": "score",
            "score_result": result.model_dump(mode="json", exclude_none=False),
            "final_answer": "无法评分：缺少招聘信息。",
        }

    if not resume_summary_data:
        result = _build_blocked_score_result(
            message="resume_summary is empty",
            suggestion="先完成简历抽取，再进行岗位匹配评分。",
            upstream_error=upstream_error,
        )
        return {
            "node": "end",
            "processing_stage": "score",
            "score_result": result.model_dump(mode="json", exclude_none=False),
            "final_answer": "无法评分：缺少结构化简历信息。",
        }

    try:
        summary = ResumeSummary.model_validate(resume_summary_data)
    except Exception as exc:
        result = _build_blocked_score_result(
            message=f"resume_summary validation failed: {exc}",
            suggestion="修正 SummaryNode 输出结构后再评分。",
            upstream_error=upstream_error,
        )
        return {
            "node": "end",
            "processing_stage": "score",
            "score_result": result.model_dump(mode="json", exclude_none=False),
            "final_answer": "无法评分：简历结构化结果无效。",
        }

    verify_result = _load_verify_result(verify_result_data)

    score_result = _score_resume(summary, verify_result, job_text, upstream_error)

    return {
        "node": "end",
        "processing_stage": "score",
        "score_result": score_result.model_dump(mode="json", exclude_none=False),
        "final_answer": _build_final_answer(score_result),
    }


def _build_blocked_score_result(
    message: str,
    suggestion: str,
    upstream_error: str | None,
) -> ScoreResult:
    """当评分前置条件不足时，返回统一的 blocked 结果。"""

    return ScoreResult(
        overall_status="blocked",
        upstream_error=upstream_error,
        reason=ScoreReason(
            why_this_score=message,
            risk_points=[message],
        ),
        improvement_suggestions=[suggestion],
        generated_at=_now_iso(),
    )


def _load_verify_result(verify_result_data: dict[str, Any]) -> VerifyResult | None:
    """
    尝试把 verify_result 恢复成结构化模型。

    评分可以在缺少 verify_result 的情况下继续执行，只是风险信息会变弱。
    """

    if not verify_result_data:
        return None

    try:
        return VerifyResult.model_validate(verify_result_data)
    except Exception:
        return None


def _score_resume(
    summary: ResumeSummary,
    verify_result: VerifyResult | None,
    job_text: str,
    upstream_error: str | None,
) -> ScoreResult:
    """
    调用模型生成岗位匹配分数和原因。

    输入里会同时包含：
    - JD 文本
    - 结构化简历
    - 核验结果
    - 上游错误

    这样模型不仅看“会什么”，还能看“信息是否可信、是否缺失”。
    """

    extractor = llm.with_structured_output(ScoreResult, method="function_calling")
    scoring_input = {
        "job_text": job_text,
        "resume_summary": summary.model_dump(mode="json", exclude_none=False),
        "verify_result": verify_result.model_dump(mode="json", exclude_none=False) if verify_result else None,
        "upstream_error": upstream_error,
    }

    result: Any = extractor.invoke(
        [
            SystemMessage(content=SCORING_PROMPT),
            HumanMessage(
                content=(
                    "请根据以下岗位信息、简历摘要和核验结果输出结构化评分结果。\n"
                    f"{scoring_input}"
                )
            ),
        ]
    )

    score_result = _coerce_score_result(result)
    score_result.generated_at = score_result.generated_at or _now_iso()
    score_result.upstream_error = score_result.upstream_error or upstream_error
    score_result.score = _normalize_score_breakdown(score_result.score)
    return score_result


def _coerce_score_result(result: Any) -> ScoreResult:
    """把 LLM 返回值收敛为 ScoreResult。"""

    if isinstance(result, ScoreResult):
        return result
    if isinstance(result, dict):
        return ScoreResult.model_validate(result)
    raise TypeError(f"unexpected score output type: {type(result)!r}")


def _normalize_score_breakdown(score: ScoreBreakdown) -> ScoreBreakdown:
    """兜底把分数裁剪到 0-100，避免模型偶发输出越界值。"""

    return ScoreBreakdown(
        overall=_clamp_score(score.overall),
        must_have_match=_clamp_score(score.must_have_match),
        experience_match=_clamp_score(score.experience_match),
        skill_match=_clamp_score(score.skill_match),
        education_match=_clamp_score(score.education_match),
    )


def _clamp_score(value: int) -> int:
    """把单个分数限制在 0-100 区间。"""

    return max(0, min(100, int(value)))


def _build_final_answer(score_result: ScoreResult) -> str:
    """生成一个可直接展示的简短评分结论。"""

    if score_result.overall_status == "blocked":
        return f"无法完成岗位评分：{score_result.reason.why_this_score}"

    met_text = "；".join(score_result.reason.met_requirements[:2]) or "暂无明确匹配亮点"
    missing_text = "；".join(score_result.reason.missing_requirements[:2]) or "暂无明显缺口"
    return (
        f"岗位匹配得分 {score_result.score.overall}/100。"
        f"匹配亮点：{met_text}。"
        f"主要缺口：{missing_text}。"
    )


def _now_iso() -> str:
    """统一生成 UTC 时间字符串，格式为 YYYY-MM-DD HH:MM:SS。"""

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
