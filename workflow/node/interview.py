from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from workflow.llm import llm
from workflow.node.summary import ResumeSummary
from workflow.state import CVState


QuestionCategory = Literal["simple", "senior", "project", "bonus"]


class InterviewQuestion(BaseModel):
    question: str = Field(..., description="面试问题")
    answer: str = Field(..., description="参考答案")
    why_ask: str = Field(..., description="为什么要问这道题")


class InterviewSection(BaseModel):
    category: QuestionCategory
    title: str
    description: str
    questions: list[InterviewQuestion] = Field(default_factory=list)


class InterviewResult(BaseModel):
    overall_summary: str = ""
    sections: list[InterviewSection] = Field(default_factory=list)


class InterviewSectionDraft(BaseModel):
    title: str
    description: str
    questions: list[InterviewQuestion] = Field(default_factory=list)


INTERVIEW_PROMPT = """
你是公司的资深技术面试官。你的任务是基于岗位描述和候选人的结构化简历，产出一套高质量面试题。

请严格遵守以下规则：
1. 问题必须分成四类：
   - simple：基础题，考察候选人简历中直接相关的基础知识
   - senior：资深题，考察技术深度、原理理解、架构思维和边界处理
   - project：项目题，必须针对候选人写过的项目或经历深挖细节，不能空泛
   - bonus：附加题，根据 job 中出现但候选人简历没有明确体现的技术点继续追问
2. 每一类都必须输出 5 到 8 道题，不能少于 5 道。
3. 每一道题都必须包含：
   - question：面试问题
   - answer：参考答案，要具体，不能只写关键词
   - why_ask：提问目的
4. project 类问题必须真正深挖项目细节，例如：
   - 设计方案为什么这样选
   - 遇到过什么问题，怎么排查
   - 指标或结果怎么证明
   - 如果重做会怎么优化
5. bonus 类问题必须优先针对岗位里明确写到、但简历里没有明显体现的技术或经验。
6. 不要编造候选人没有写过的项目；但可以基于岗位要求补充 bonus 类追问。
7. overall_summary 用中文简洁概括这套题的考察重点。
8. 严格按给定结构返回。
"""


def InterviewNode(state: CVState) -> CVState:
    resume_summary_data = state.get("resume_summary") or {}
    job_text = (state.get("job_text") or "").strip()
    upstream_error = state.get("error")

    if not resume_summary_data:
        return {
            "node": "end",
            "processing_stage": "interview",
            "interview_result": InterviewResult(
                overall_summary="无法生成面试题：缺少结构化简历。",
                sections=[],
            ).model_dump(mode="json", exclude_none=False),
        }

    if not job_text:
        return {
            "node": "end",
            "processing_stage": "interview",
            "interview_result": InterviewResult(
                overall_summary="无法生成面试题：缺少岗位描述。",
                sections=[],
            ).model_dump(mode="json", exclude_none=False),
        }

    try:
        summary = ResumeSummary.model_validate(resume_summary_data)
    except Exception as exc:
        return {
            "node": "end",
            "processing_stage": "interview",
            "interview_result": InterviewResult(
                overall_summary=f"无法生成面试题：resume_summary validation failed: {exc}",
                sections=[],
            ).model_dump(mode="json", exclude_none=False),
        }

    interview_result = _generate_interview_questions(summary, job_text, upstream_error)

    return {
        "node": "end",
        "processing_stage": "interview",
        "interview_result": interview_result.model_dump(mode="json", exclude_none=False),
    }


def _generate_interview_questions(
    summary: ResumeSummary,
    job_text: str,
    upstream_error: str | None,
) -> InterviewResult:
    sections = [
        _generate_interview_section(summary, job_text, upstream_error, category="simple"),
        _generate_interview_section(summary, job_text, upstream_error, category="senior"),
        _generate_interview_section(summary, job_text, upstream_error, category="project"),
        _generate_interview_section(summary, job_text, upstream_error, category="bonus"),
    ]

    interview_result = InterviewResult(
        overall_summary=(
            "本套面试题覆盖基础能力、技术深度、项目细节以及岗位要求中的能力缺口，"
            "可用于分阶段评估候选人的知识广度、实战深度和岗位匹配度。"
        ),
        sections=sections,
    )
    _ensure_interview_sections(interview_result)
    return interview_result


def _generate_interview_section(
    summary: ResumeSummary,
    job_text: str,
    upstream_error: str | None,
    *,
    category: QuestionCategory,
) -> InterviewSection:
    title_map = {
        "simple": "基础题",
        "senior": "资深题",
        "project": "项目题",
        "bonus": "附加题",
    }
    description_map = {
        "simple": "考察候选人的基础知识掌握情况",
        "senior": "考察候选人的技术深度和架构理解",
        "project": "深挖候选人项目细节与落地能力",
        "bonus": "针对岗位要求中简历未充分体现的技术继续追问",
    }
    category_instruction_map = {
        "simple": "只生成基础题，围绕候选人简历中明确写到的技术基础和岗位基础能力提问。",
        "senior": "只生成资深题，重点考察技术原理、设计取舍、复杂问题处理和工程深度。",
        "project": "只生成项目题，必须针对简历中明确写过的项目或经历深挖细节，问题要具体。",
        "bonus": "只生成附加题，优先针对 job 中明确要求但简历中未充分体现的技术点继续追问。",
    }
    extractor = llm.with_structured_output(InterviewSectionDraft, method="function_calling")
    interview_input = {
        "job_text": job_text,
        "resume_summary": summary.model_dump(mode="json", exclude_none=False),
        "upstream_error": upstream_error,
        "category": category,
    }

    result = extractor.invoke(
        [
            SystemMessage(
                content=(
                    f"{INTERVIEW_PROMPT}\n\n"
                    f"当前只生成 `{category}` 这一类题目。\n"
                    f"{category_instruction_map[category]}\n"
                    "当前输出必须包含 5 到 8 道题，每道题必须有 question、answer、why_ask。"
                )
            ),
            HumanMessage(
                content=(
                    "请根据以下岗位信息和结构化简历，生成当前分类的面试题与参考答案。\n"
                    f"{interview_input}"
                )
            ),
        ]
    )

    if result is None:
        raise TypeError(f"interview section `{category}` returned None")

    if isinstance(result, dict):
        result = InterviewSectionDraft.model_validate(result)
    elif not isinstance(result, InterviewSectionDraft):
        raise TypeError(f"unexpected interview section output type: {type(result)!r}")

    questions = result.questions[:8]
    if not questions:
        raise ValueError(f"interview section `{category}` returned empty questions")

    return InterviewSection(
        category=category,
        title=result.title or title_map[category],
        description=result.description or description_map[category],
        questions=questions,
    )


def _ensure_interview_sections(interview_result: InterviewResult) -> None:
    expected_categories: list[tuple[QuestionCategory, str, str]] = [
        ("simple", "基础题", "考察候选人的基础知识掌握情况"),
        ("senior", "资深题", "考察候选人的技术深度和架构理解"),
        ("project", "项目题", "深挖候选人项目细节与落地能力"),
        ("bonus", "附加题", "针对岗位要求中简历未充分体现的技术继续追问"),
    ]

    existing = {section.category for section in interview_result.sections}
    for category, title, description in expected_categories:
        if category not in existing:
            interview_result.sections.append(
                InterviewSection(
                    category=category,
                    title=title,
                    description=description,
                    questions=[],
                )
            )
