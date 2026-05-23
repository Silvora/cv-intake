from langgraph.graph import StateGraph, START, END
from workflow.state import State
from workflow.node.summary import SummaryNode
from workflow.node.verify import VerifyNode
from workflow.node.score import ScoreNode
from typing import cast


# 这是 LangGraph 的工作流装配文件：
# SummaryNode -> VerifyNode -> ScoreNode
# API 层不关心节点内部实现，只通过 run_cv_workflow(...) 把输入交给整条图执行。
state = State(node="", final_answer="")

graph = StateGraph(State)
# 添加节点
graph.add_node("summary", SummaryNode)
graph.add_node("verify", VerifyNode)
graph.add_node("score", ScoreNode)

# 添加边
graph.add_edge(START, "summary")
graph.add_edge("summary", "verify")
graph.add_edge("verify", "score")
graph.add_edge("score", END)

# 编译图
app = graph.compile()

# 运行图
# result = app.invoke(state)
# print(result)

def run_cv_workflow(resume_text: str, job_text: str) -> State:
    """
    统一封装简历工作流入口，供 API 层调用。

    输入是两段原始文本：
    - resume_text：OCR 后的简历正文
    - job_text：岗位描述/JD

    输出是完整 state，里面会逐步包含：
    - resume_summary
    - verify_result
    - score_result
    - final_answer
    """

    initial_state: State = {
        "node": "summary",
        "resume_text": resume_text,
        "job_text": job_text,
        "final_answer": "",
    }
    result = app.invoke(initial_state)
    if not isinstance(result, dict):
        raise TypeError(f"unexpected workflow result type: {type(result)!r}")
    return cast(State, result)
