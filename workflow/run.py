from langgraph.graph import StateGraph, START, END
from langgraph.errors import NodeError
from langgraph.types import RetryPolicy

from workflow.state import CVState
from workflow.node.summary import SummaryNode
from workflow.node.verify import VerifyNode, _build_blocked_verify_result
from workflow.node.score import ScoreNode, _build_blocked_score_result
from workflow.node.interview import InterviewNode, InterviewResult

from typing import cast


# 这是 LangGraph 的工作流装配文件。
# 这里负责两件事：
# 1. 定义节点执行顺序
# 2. 为每个节点统一挂上重试和失败兜底逻辑
graph = StateGraph(CVState)


def _retry_all_exceptions(exc: BaseException) -> bool:
    """
    让 LangGraph 对当前节点抛出的常规异常都执行重试。

    这里故意放宽到所有 Exception：
    - LLM 输出为空 / 结构不匹配
    - 上游 SDK 报临时错误
    - 网络抖动
    都先重试，再交给 error_handler 收口。
    """
    return isinstance(exc, Exception)


# 所有节点共用同一套重试策略：
# 最多 3 次，初始等待 1 秒，每次按 2 倍退避。
NODE_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    retry_on=_retry_all_exceptions,
)


def _summary_error_handler(state: CVState, error: NodeError) -> CVState:
    """
    SummaryNode 重试耗尽后的兜底处理。

    约定：
    - 继续流转到 verify
    - 把结构化摘要置空
    - 错误信息写到 state["error"]，供下游感知
    """
    return {
        "node": "verify",
        "resume_summary": {},
        "error": f"summary extraction failed: {error.error}",
    }


def _verify_error_handler(state: CVState, error: NodeError) -> CVState:
    """
    VerifyNode 重试耗尽后的兜底处理。

    这里复用 VerifyNode 内部的 blocked 结果构造函数，
    保证失败时的数据结构与节点内主动降级保持一致。
    """
    result = _build_blocked_verify_result(
        message=f"verify generation failed: {error.error}",
        suggestion="检查模型联网核验能力或 VerifyNode 输入数据。",
        upstream_error=state.get("error"),
    )
    return {
        "node": "score",
        "verify_result": result.model_dump(mode="json", exclude_none=False),
    }


def _score_error_handler(state: CVState, error: NodeError) -> CVState:
    """
    ScoreNode 重试耗尽后的兜底处理。

    评分失败后直接结束主流程，并给前端一个可展示的 final_answer。
    """
    result = _build_blocked_score_result(
        message=f"score generation failed: {error.error}",
        suggestion="检查评分模型调用和输入数据是否正常。",
        upstream_error=state.get("error"),
    )
    return {
        "node": "end",
        "score_result": result.model_dump(mode="json", exclude_none=False),
        "final_answer": "无法评分：评分模型调用失败。",
    }


def _interview_error_handler(state: CVState, error: NodeError) -> CVState:
    """
    InterviewNode 重试耗尽后的兜底处理。

    面试题失败不影响前面的摘要、核验和评分结果，
    因此这里只返回一个空 sections 的 interview_result。
    """
    result = InterviewResult(
        overall_summary=f"面试题生成失败：{error.error}",
        sections=[],
    )
    return {
        "node": "end",
        "interview_result": result.model_dump(mode="json", exclude_none=False),
    }


# 节点注册：
# - retry_policy 负责真正的自动重试
# - error_handler 负责“重试仍失败”后的结构化兜底
graph.add_node(
    "summary",
    SummaryNode,
    retry_policy=NODE_RETRY_POLICY,
    error_handler=_summary_error_handler,
)
graph.add_node(
    "verify",
    VerifyNode,
    retry_policy=NODE_RETRY_POLICY,
    error_handler=_verify_error_handler,
)
graph.add_node(
    "score",
    ScoreNode,
    retry_policy=NODE_RETRY_POLICY,
    error_handler=_score_error_handler,
)
graph.add_node(
    "interview",
    InterviewNode,
    retry_policy=NODE_RETRY_POLICY,
    error_handler=_interview_error_handler,
)

# 工作流顺序：
# summary -> verify -> score -> interview
graph.add_edge(START, "summary")
graph.add_edge("summary", "verify")
graph.add_edge("verify", "score")
graph.add_edge("score", "interview")
graph.add_edge("interview", END)

# 编译 LangGraph，得到可直接 invoke 的运行对象。
app = graph.compile()


def build_initial_state(
    cv_id: str,
    cv_name: str,
    resume_text: str,
    job_text: str,
) -> CVState:
    return {
        "cv_id": cv_id,
        "cv_name": cv_name,
        "node": "summary",
        "processing_stage": "summary",
        "resume_text": resume_text,
        "job_text": job_text,
        "final_answer": "",
    }


def stream_cv_workflow(cv_id: str, cv_name: str, resume_text: str, job_text: str):
    initial_state = build_initial_state(cv_id, cv_name, resume_text, job_text)
    return app.stream(initial_state, stream_mode="updates")


def run_cv_workflow(cv_id: str, cv_name: str, resume_text: str, job_text: str) -> CVState:
    """
    统一封装简历工作流入口，供 API 层调用。

    输入是两段原始文本：
    - resume_text：OCR 后的简历正文
    - job_text：岗位描述/JD

    输出是完整 state，里面会逐步包含：
    - resume_summary
    - verify_result
    - score_result
    - interview_result
    - final_answer
    """

    initial_state = build_initial_state(cv_id, cv_name, resume_text, job_text)
    result = app.invoke(initial_state)
    if not isinstance(result, dict):
        raise TypeError(f"unexpected workflow result type: {type(result)!r}")
    return cast(CVState, result)
