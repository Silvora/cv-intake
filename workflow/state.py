from typing import Any, TypedDict


# State：工作流中所有节点都能读写的共享数据。
# total=False 允许节点只返回本次更新的字段，由 LangGraph 合并进全量状态。
class CVState(TypedDict, total=False):
    # id 简历标识
    cv_id: str
    # name 简历名称
    cv_name: str
    # node 主要用于表达当前流转阶段，便于调试和日志定位。
    node: str
    # 当前处理阶段，供 SSE 和前端展示。
    processing_stage: str
    # 当前阶段的执行次数，供重试和前端展示。
    processing_attempt: int
    # OCR 提取出的原始简历文本。
    resume_text: str
    # SummaryNode 产出的结构化简历摘要。
    resume_summary: dict[str, Any]
    # VerifyNode 产出的核验结果。
    verify_result: dict[str, Any]
    # ScoreNode 产出的评分结果。
    score_result: dict[str, Any]
    # InterviewNode 产出的面试题结果。
    interview_result: dict[str, Any]
    # 岗位描述文本，由 API 层在上传时注入。
    job_text: str
    # 便于直接展示的最终简短结论。
    final_answer: str
    # 工作流任意阶段的错误或警告信息。
    error: str | None
