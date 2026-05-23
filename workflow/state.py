from typing import Any, TypedDict


# State：工作流中所有节点都能读写的共享数据。
# total=False 允许节点只返回本次更新的字段，由 LangGraph 合并进全量状态。
class State(TypedDict, total=False):
    # node 主要用于表达当前流转阶段，便于调试和日志定位。
    node: str
    # OCR 提取出的原始简历文本。
    resume_text: str
    # SummaryNode 产出的结构化简历摘要。
    resume_summary: dict[str, Any]
    # VerifyNode 产出的核验结果。
    verify_result: dict[str, Any]
    # ScoreNode 产出的评分结果。
    score_result: dict[str, Any]
    # 岗位描述文本，由 API 层在上传时注入。
    job_text: str
    # 便于直接展示的最终简短结论。
    final_answer: str
    # 工作流任意阶段的错误或警告信息。
    error: str | None
