from typing import Any, List, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from workflow.llm import llm
from workflow.state import State


# SummaryNode 的职责很单一：把 OCR 文本转成结构化简历。
# 它不负责事实核验，也不负责岗位匹配评分。
class User(BaseModel):
    name: Optional[str] = Field(None, description="用户姓名")
    gender: Optional[str] = Field(None, description="性别（Male/Female/Other）")
    birth_date: Optional[str] = Field(None, description="出生日期（YYYY-MM-DD）")
    nationality: Optional[str] = Field(None, description="国籍")
    location: Optional[str] = Field(None, description="现居城市/地区")
    email: Optional[str] = Field(None, description="电子邮箱地址")
    phone: Optional[str] = Field(None, description="电话号码")
    linkedin: Optional[str] = Field(None, description="LinkedIn 链接")
    github: Optional[str] = Field(None, description="GitHub 链接")
    current_job_title: Optional[str] = Field(None, description="当前（或最近）职位名称")
    desired_job_title: Optional[str] = Field(None, description="期望职位/求职意向")
    school: Optional[str] = Field(None, description="毕业院校或就读学校")
    summary: Optional[str] = Field(None, description="个人简介或自我评价")

class Education(BaseModel):
    """单个教育经历"""
    school: str = Field(..., description="学校名称")
    degree: Optional[str] = Field(None, description="学位，例如本科、硕士")
    major: Optional[str] = Field(None, description="专业名称")
    start_date: Optional[str] = Field(None, description="开始时间，格式 YYYY-MM-DD 或 YYYY-MM")
    end_date: Optional[str] = Field(None, description="结束时间，格式同上，若至今则填 'Present'")
    description: Optional[str] = Field(None, description="补充说明，例如绩点、主修课程、荣誉")

class WorkExperience(BaseModel):
    """单个工作经历"""
    company: str = Field(..., description="公司名称")
    title: Optional[str] = Field(None, description="职位名称")
    start_date: Optional[str] = Field(None, description="开始时间，格式 YYYY-MM-DD 或 YYYY-MM")
    end_date: Optional[str] = Field(None, description="结束时间，格式同上，若至今则填 'Present'")
    location: Optional[str] = Field(None, description="工作地点")
    description: Optional[str] = Field(None, description="职责与成果概述")

class Skill(BaseModel):
    """单个技能项"""
    name: str = Field(..., description="技能名称，例如：Python、项目管理、Photoshop")
    level: Optional[str] = Field(None, description="熟练程度，例如：精通、熟练、了解、中级")

class Project(BaseModel):
    """单个项目经历"""
    name: str = Field(..., description="项目名称")
    role: Optional[str] = Field(None, description="在项目中担任的角色，例如：核心开发、项目经理")
    start_date: Optional[str] = Field(None, description="项目开始时间，格式 YYYY-MM-DD 或 YYYY-MM")
    end_date: Optional[str] = Field(None, description="项目结束时间，格式同上，若至今则填 'Present'")
    description: Optional[str] = Field(None, description="项目描述，主要职责和成果")
    tech_stack: Optional[List[str]] = Field(None, description="项目中使用的技术栈，例如 ['React', 'FastAPI', 'MongoDB']")
    link: Optional[str] = Field(None, description="项目链接（GitHub、在线演示等）")

class Award(BaseModel):
    """单个获奖/荣誉"""
    name: str = Field(..., description="奖项名称，例如：国家奖学金、ACM 省赛一等奖")
    date: Optional[str] = Field(None, description="获奖时间，格式 YYYY-MM-DD 或 YYYY")
    level: Optional[str] = Field(None, description="奖项级别，例如：国家级、省级、校级")
    description: Optional[str] = Field(None, description="补充说明，如获奖比例、授予单位")

class OtherItem(BaseModel):
    """其它信息条目（证书、语言、爱好、社会活动等）"""
    category: str = Field(..., description="类别，例如：证书、语言、兴趣爱好、志愿者活动")
    name: str = Field(..., description="具体名称，例如：CET-6、钢琴、篮球")
    detail: Optional[str] = Field(None, description="详情，如分数、等级、简单描述")


def _default_user() -> User:
    """给 Pydantic default_factory 用的零参工厂。"""
    return User.model_validate({})


class ResumeSummary(BaseModel):
    """简历结构化摘要"""
    user: User = Field(default_factory=_default_user, description="候选人基础信息")
    education: List[Education] = Field(default_factory=list, description="教育经历列表")
    work_experiences: List[WorkExperience] = Field(default_factory=list, description="工作经历列表")
    skills: List[Skill] = Field(default_factory=list, description="技能列表")
    projects: List[Project] = Field(default_factory=list, description="项目经历列表")
    awards: List[Award] = Field(default_factory=list, description="获奖经历列表")
    others: List[OtherItem] = Field(default_factory=list, description="其他补充信息")

SUMMARY_PROMPT = """
你是一个简历信息抽取器。输入是一段 OCR 识别后的简历文本，可能存在错字、换行错位、重复符号和版式丢失。

请输出结构化简历摘要，并严格遵守以下规则：
1. 只能根据输入文本提取，不要臆测或补全缺失事实。
2. 无法确定的单值字段填 null。
3. 列表字段如果没有内容，返回 []。
4. 日期尽量标准化为 YYYY-MM-DD 或 YYYY-MM；如果只能确定年份，则输出 YYYY；完全无法判断则填 null。
5. 当前仍在进行的经历，结束时间统一填 "Present"。
6. 优先保留简历原文语义，不要扩写和润色。
7. 如果 OCR 文本有噪点，请尽量基于上下文纠正理解后再提取。
"""


def _normalize_resume_text(resume_text: str) -> str:
    """先做一层轻量清洗，降低 OCR 空行和杂乱换行对抽取的干扰。"""
    cleaned_lines = [line.strip() for line in resume_text.splitlines()]
    return "\n".join(line for line in cleaned_lines if line)


def _extract_resume_summary(resume_text: str) -> ResumeSummary:
    """调用模型，把清洗后的简历文本抽取成 ResumeSummary。"""
    extractor = llm.with_structured_output(ResumeSummary, method="function_calling")
    result: Any = extractor.invoke(
        [
            SystemMessage(content=SUMMARY_PROMPT),
            HumanMessage(content=f"简历 OCR 文本如下：\n{resume_text}"),
        ]
    )

    if isinstance(result, ResumeSummary):
        return result
    if isinstance(result, dict):
        return ResumeSummary.model_validate(result)

    raise TypeError(f"unexpected summary output type: {type(result)!r}")


def SummaryNode(state: State) -> State:
    """
    工作流第一站：简历结构化抽取。

    输入：
    - state["resume_text"]

    输出：
    - state["resume_summary"]
    - state["error"]（若抽取失败）
    """
    resume_text = (state.get("resume_text") or "").strip()
    if not resume_text:
        return {
            "node": "verify",
            "resume_summary": {},
            "error": "resume_text is empty",
        }

    normalized_text = _normalize_resume_text(resume_text)

    try:
        summary = _extract_resume_summary(normalized_text)
    except Exception as exc:
        # 抽取失败时不抛异常中断工作流，而是把错误写入 state 继续下游。
        return {
            "node": "verify",
            "resume_summary": {},
            "error": f"summary extraction failed: {exc}",
        }

    return {
        "node": "verify",
        "resume_summary": summary.model_dump(mode="json", exclude_none=False),
        "error": None,
    }
