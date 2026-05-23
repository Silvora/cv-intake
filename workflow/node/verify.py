from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from zai import ZhipuAiClient

from config.app import appConfig
from workflow.llm import llm
from workflow.node.summary import ResumeSummary
from workflow.state import State


# VerifyNode 现在只做你关心的三类核验：
# 1. 学校：学校简介、层次标签
# 2. 公司：公司简介、经营范围、代表项目/产品
# 3. 工作时间：起止时间是否前后合理、是否明显冲突

ZHIPU_VERIFY_TIMEOUT_SECONDS = 60.0
ZHIPU_WEB_SEARCH_ENGINE = "search_pro"
ZHIPU_WEB_SEARCH_COUNT = 8


class VerificationIssue(BaseModel):
    """统一的问题项，供后续评分或前端直接消费。"""

    severity: str
    category: str
    subject: str
    message: str
    suggestion: str | None = None


class SearchEvidence(BaseModel):
    """前端可直接展示的单条搜索证据。"""

    title: str
    snippet: str | None = None
    link: str | None = None
    media: str | None = None
    publish_date: str | None = None


class SchoolVerification(BaseModel):
    """单个学校的核验结果。"""

    school: str
    verified: bool | None = None
    school_levels: list[str] = Field(default_factory=list)
    profile: str | None = None
    reason: str | None = None
    evidence: list[SearchEvidence] = Field(default_factory=list)


class CompanyVerification(BaseModel):
    """单个公司的核验结果。"""

    company: str
    verified: bool | None = None
    profile: str | None = None
    business_scope: str | None = None
    representative_projects: list[str] = Field(default_factory=list)
    reason: str | None = None
    evidence: list[SearchEvidence] = Field(default_factory=list)


class WorkDateVerification(BaseModel):
    """单段工作经历的时间核验结果。"""

    company: str
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    date_consistent: bool | None = None
    reason: str | None = None


class VerifyResult(BaseModel):
    """VerifyNode 的简化输出结构。"""

    overall_status: str = "partially_verified"
    upstream_error: str | None = None
    verification_summary: str = ""
    schools: list[SchoolVerification] = Field(default_factory=list)
    companies: list[CompanyVerification] = Field(default_factory=list)
    work_dates: list[WorkDateVerification] = Field(default_factory=list)
    issues: list[VerificationIssue] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


VERIFY_PROMPT = """
你是一个简历信息核验器。你的任务是基于结构化简历，输出学校、公司和工作时间的核验结果。

请严格遵守以下规则：
1. 核验范围只包括：
   - 学校：学校简介、学校层次标签（如 985 / 211 / 双一流 / 海外高校等）
   - 公司：公司简介、经营范围/主营业务、代表项目或产品
   - 工作时间：每段工作经历的起止时间是否前后合理，是否与教育或其他工作经历明显冲突
2. 我会给你提供 web_search API 的联网搜索证据；你必须优先依据这些证据给出结论，不要只依赖参数中的静态知识。
3. 工作时间核验不需要联网，直接根据简历中的时间线判断是否前后合理、是否明显重叠或冲突。
4. 不要编造候选人的隐私信息，也不要伪造不存在的查询结果。
5. 无法确认时，verified 可以填 null，reason 里写清楚原因。
6. issues 只保留真正重要的问题或风险，不要塞无意义重复项。
7. verification_summary 用中文简洁概括整体核验结论。
8. overall_status 只能是 verified、partially_verified、blocked 三者之一。
9. schools 和 companies 中的 evidence 字段要保留最关键的 1 到 2 条来源摘要。
10. 严格按给定结构返回，不要漏字段。
"""


def VerifyNode(state: State) -> State:
    """
    轻量核验节点。

    输入：
    - state["resume_summary"]：SummaryNode 产出的结构化简历
    - state["error"]：上游错误或警告

    输出：
    - state["verify_result"]：简化后的核验结果
    """

    upstream_error = state.get("error")
    resume_summary_data = state.get("resume_summary") or {}

    if not resume_summary_data:
        result = _build_blocked_verify_result(
            message="resume_summary is empty",
            suggestion="先完成 SummaryNode 的结构化抽取，再进行核验。",
            upstream_error=upstream_error,
        )
        return {
            "node": "score",
            "verify_result": result.model_dump(mode="json", exclude_none=False),
        }

    try:
        summary = ResumeSummary.model_validate(resume_summary_data)
    except Exception as exc:
        result = _build_blocked_verify_result(
            message=f"resume_summary validation failed: {exc}",
            suggestion="修正 SummaryNode 输出结构后再进行核验。",
            upstream_error=upstream_error,
        )
        return {
            "node": "score",
            "verify_result": result.model_dump(mode="json", exclude_none=False),
        }

    try:
        verify_result = _verify_resume(summary, upstream_error)
    except Exception as exc:
        result = _build_blocked_verify_result(
            message=f"verify generation failed: {exc}",
            suggestion="检查模型联网核验能力或 VerifyNode 输入数据。",
            upstream_error=upstream_error,
        )
        return {
            "node": "score",
            "verify_result": result.model_dump(mode="json", exclude_none=False),
        }

    return {
        "node": "score",
        "verify_result": verify_result.model_dump(mode="json", exclude_none=False),
    }


def _build_blocked_verify_result(
    message: str,
    suggestion: str,
    upstream_error: str | None,
) -> VerifyResult:
    """当前置条件不足或模型调用失败时，返回统一的 blocked 结果。"""

    return VerifyResult(
        overall_status="blocked",
        upstream_error=upstream_error,
        verification_summary=message,
        issues=[
            VerificationIssue(
                severity="high",
                category="verify",
                subject="resume_summary",
                message=message,
                suggestion=suggestion,
            )
        ],
        next_actions=[suggestion],
    )


def _verify_resume(summary: ResumeSummary, upstream_error: str | None) -> VerifyResult:
    """
    使用智谱 SDK 发起联网核验。

    实现分两步：
    1. 直接调用 client.web_search.web_search 查询学校和公司
    2. 再把“结构化简历 + 搜索证据”交给模型，生成最终 VerifyResult
    """

    client = _build_zhipu_client()
    verify_input = {
        "resume_summary": summary.model_dump(mode="json", exclude_none=False),
        "web_search_evidence": _collect_web_search_evidence(client, summary),
        "upstream_error": upstream_error,
    }

    extractor = llm.with_structured_output(VerifyResult, method="function_calling")
    result: Any = extractor.invoke(
        [
            SystemMessage(content=_build_verify_system_prompt()),
            HumanMessage(
                content=(
                    "请根据以下结构化简历和联网搜索证据输出 VerifyResult：\n"
                    f"{json.dumps(verify_input, ensure_ascii=False)}"
                )
            ),
        ]
    )

    verify_result = _coerce_verify_result(result)
    verify_result.upstream_error = verify_result.upstream_error or upstream_error
    _attach_search_evidence(verify_result, verify_input["web_search_evidence"])
    _ensure_verification_coverage(summary, verify_result)
    return verify_result


def _coerce_verify_result(result: Any) -> VerifyResult:
    """把模型输出统一收敛成 VerifyResult。"""

    if isinstance(result, VerifyResult):
        return result
    if isinstance(result, dict):
        return VerifyResult.model_validate(result)
    raise TypeError(f"unexpected verify output type: {type(result)!r}")


def _build_zhipu_client() -> ZhipuAiClient:
    """使用配置里的智谱 API Key 创建客户端。"""

    api_key = (appConfig.zhipu.api_key or "").strip()
    if not api_key:
        raise ValueError("appConfig.zhipu.api_key is empty")
    return ZhipuAiClient(api_key=api_key)


def _build_verify_system_prompt() -> str:
    """把结果 schema 一并塞进系统提示词，降低模型输出跑偏概率。"""

    schema = VerifyResult.model_json_schema()
    return (
        f"{VERIFY_PROMPT}\n\n"
        "请严格按照以下 JSON Schema 返回：\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )


def _collect_web_search_evidence(
    client: ZhipuAiClient,
    summary: ResumeSummary,
) -> dict[str, list[dict[str, Any]]]:
    """
    显式调用 web_search API 收集学校和公司的联网证据。

    这样做的好处是：
    - 查询语句完全可控
    - 后面如果要做缓存、限流、审计都比较容易
    - 排查问题时能直接看到每个实体到底搜了什么、搜回了什么
    """

    school_evidence = [
        _search_target(
            client=client,
            target_type="school",
            target_name=school,
            search_query=f"{school} 学校简介 985 211 双一流",
        )
        for school in _collect_expected_schools(summary)
    ]

    company_evidence = [
        _search_target(
            client=client,
            target_type="company",
            target_name=company,
            search_query=f"{company} 公司简介 主营业务 经营范围 代表产品 代表项目",
        )
        for company in _collect_expected_companies(summary)
    ]

    return {
        "schools": school_evidence,
        "companies": company_evidence,
    }


def _search_target(
    client: ZhipuAiClient,
    target_type: str,
    target_name: str,
    search_query: str,
) -> dict[str, Any]:
    """对单个学校或公司发起一次显式 web_search 查询。"""

    try:
        response = client.web_search.web_search(
            search_engine=ZHIPU_WEB_SEARCH_ENGINE,
            search_query=search_query,
            count=ZHIPU_WEB_SEARCH_COUNT,
            search_recency_filter="noLimit",
            content_size="high",
            timeout=ZHIPU_VERIFY_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        return {
            "target_type": target_type,
            "target_name": target_name,
            "search_query": search_query,
            "error": str(exc),
        }

    return {
        "target_type": target_type,
        "target_name": target_name,
        "search_query": search_query,
        "response": _dump_web_search_response(response),
    }


def _dump_web_search_response(response: Any) -> dict[str, Any]:
    """把 SDK 返回的 WebSearchResp 手工转成普通 dict，避开 SDK/Pydantic 序列化兼容问题。"""

    if isinstance(response, dict):
        return response
    return {
        "created": getattr(response, "created", None),
        "request_id": getattr(response, "request_id", None),
        "id": getattr(response, "id", None),
        "search_intent": _dump_web_search_intent(getattr(response, "search_intent", None)),
        "search_result": _dump_web_search_result(getattr(response, "search_result", None)),
    }


def _dump_web_search_intent(search_intent: Any) -> dict[str, Any] | None:
    """手工提取 search_intent 字段。"""

    if search_intent is None:
        return None
    if isinstance(search_intent, dict):
        return search_intent
    return {
        "query": getattr(search_intent, "query", None),
        "intent": getattr(search_intent, "intent", None),
        "keywords": getattr(search_intent, "keywords", None),
    }


def _dump_web_search_result(search_result: Any) -> dict[str, Any] | None:
    """手工提取 search_result 字段。"""

    if search_result is None:
        return None
    if isinstance(search_result, dict):
        return search_result
    return {
        "title": getattr(search_result, "title", None),
        "link": getattr(search_result, "link", None),
        "content": getattr(search_result, "content", None),
        "icon": getattr(search_result, "icon", None),
        "media": getattr(search_result, "media", None),
        "refer": getattr(search_result, "refer", None),
        "publish_date": getattr(search_result, "publish_date", None),
        "images": getattr(search_result, "images", None),
    }


def _attach_search_evidence(
    verify_result: VerifyResult,
    web_search_evidence: dict[str, list[dict[str, Any]]],
) -> None:
    """
    从原始 web_search 返回里提取可展示证据，并挂到学校/公司结果上。

    这样即使模型漏填 evidence，前端仍然能看到搜索来源。
    """

    school_evidence_map = _build_evidence_map(web_search_evidence.get("schools") or [])
    for item in verify_result.schools:
        if not item.evidence:
            item.evidence = school_evidence_map.get(item.school, [])

    company_evidence_map = _build_evidence_map(web_search_evidence.get("companies") or [])
    for item in verify_result.companies:
        if not item.evidence:
            item.evidence = company_evidence_map.get(item.company, [])


def _build_evidence_map(items: list[dict[str, Any]]) -> dict[str, list[SearchEvidence]]:
    """把搜索结果列表按实体名称聚合成 evidence map。"""

    evidence_map: dict[str, list[SearchEvidence]] = {}
    for item in items:
        target_name = str(item.get("target_name") or "").strip()
        if not target_name:
            continue
        evidence_map[target_name] = _extract_search_evidence_items(item)[:2]
    return evidence_map


def _extract_search_evidence_items(item: dict[str, Any]) -> list[SearchEvidence]:
    """
    从单次 web_search 返回中提取 1-N 条候选证据。

    SDK 的实际返回结构可能有轻微差异，这里做宽松兼容：
    - `search_result` 可能是单个 dict
    - 也可能是 list
    - 某些返回可能在 `choices[].message.tool_calls[]` 里
    """

    response = item.get("response")
    if not isinstance(response, dict):
        return []

    candidates = _collect_search_result_candidates(response)
    seen: set[tuple[str, str]] = set()
    evidence_items: list[SearchEvidence] = []
    for candidate in candidates:
        evidence = _build_search_evidence(candidate)
        if evidence is None:
            continue

        dedupe_key = (evidence.title, evidence.link or "")
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        evidence_items.append(evidence)

    return evidence_items


def _collect_search_result_candidates(response: dict[str, Any]) -> list[dict[str, Any]]:
    """兼容不同 web_search 返回形态，统一抽取候选搜索结果。"""

    candidates: list[dict[str, Any]] = []
    _extend_search_result_candidates(candidates, response.get("search_result"))

    choices = response.get("choices")
    if not isinstance(choices, list):
        return candidates

    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            _extend_search_result_candidates(candidates, tool_call.get("search_result"))

    return candidates


def _extend_search_result_candidates(
    candidates: list[dict[str, Any]],
    raw_result: Any,
) -> None:
    """把单个 dict 或 list 形式的 search_result 追加进候选列表。"""

    if isinstance(raw_result, dict):
        candidates.append(raw_result)
        return

    if isinstance(raw_result, list):
        candidates.extend(entry for entry in raw_result if isinstance(entry, dict))


def _build_search_evidence(candidate: dict[str, Any]) -> SearchEvidence | None:
    """把单条搜索结果转换成前端可展示的 evidence。"""

    title = str(candidate.get("title") or "").strip()
    link = str(candidate.get("link") or "").strip()
    if not title and not link:
        return None

    return SearchEvidence(
        title=title or "未命名来源",
        snippet=_clean_snippet(candidate.get("content")),
        link=link or None,
        media=str(candidate.get("media") or "").strip() or None,
        publish_date=str(candidate.get("publish_date") or "").strip() or None,
    )


def _clean_snippet(value: Any) -> str | None:
    """截断搜索摘要，避免 verify_result 过大。"""

    if not isinstance(value, str):
        return None
    snippet = " ".join(value.split()).strip()
    if not snippet:
        return None
    if len(snippet) > 220:
        return f"{snippet[:217]}..."
    return snippet


def _ensure_verification_coverage(summary: ResumeSummary, verify_result: VerifyResult) -> None:
    """
    给模型输出补齐最基本的覆盖面。

    如果模型漏掉了某个学校、公司或工作时间段，就补一个占位结果，
    避免前端或评分节点误以为这段经历不存在。
    """

    expected_schools = _collect_expected_schools(summary)
    verified_schools = {item.school for item in verify_result.schools}
    for school in expected_schools:
        if school not in verified_schools:
            verify_result.schools.append(
                SchoolVerification(
                    school=school,
                    verified=None,
                    reason="模型未返回该学校的核验结果。",
                )
            )

    expected_companies = _collect_expected_companies(summary)
    verified_companies = {item.company for item in verify_result.companies}
    for company in expected_companies:
        if company not in verified_companies:
            verify_result.companies.append(
                CompanyVerification(
                    company=company,
                    verified=None,
                    reason="模型未返回该公司的核验结果。",
                )
            )

    verified_work_dates = {
        (item.company, item.title or "", item.start_date or "", item.end_date or "")
        for item in verify_result.work_dates
    }
    for item in summary.work_experiences:
        identity = (item.company, item.title or "", item.start_date or "", item.end_date or "")
        if identity not in verified_work_dates:
            verify_result.work_dates.append(
                WorkDateVerification(
                    company=item.company,
                    title=item.title,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    date_consistent=None,
                    reason="模型未返回该段工作时间核验结果。",
                )
            )

    if (
        verify_result.overall_status == "verified"
        and (
            len(verified_schools) < len(expected_schools)
            or len(verified_companies) < len(expected_companies)
            or len(verified_work_dates) < len(summary.work_experiences)
        )
    ):
        verify_result.overall_status = "partially_verified"


def _collect_expected_schools(summary: ResumeSummary) -> list[str]:
    """汇总简历里提到的学校名称，供覆盖面补齐使用。"""

    schools: list[str] = []
    seen: set[str] = set()

    for item in summary.education:
        school = item.school.strip()
        if school and school not in seen:
            seen.add(school)
            schools.append(school)

    user_school = (summary.user.school or "").strip()
    if user_school and user_school not in seen:
        seen.add(user_school)
        schools.append(user_school)

    return schools


def _collect_expected_companies(summary: ResumeSummary) -> list[str]:
    """汇总简历里提到的公司名称，避免重复查询同一家公司。"""

    companies: list[str] = []
    seen: set[str] = set()

    for item in summary.work_experiences:
        company = item.company.strip()
        if company and company not in seen:
            seen.add(company)
            companies.append(company)

    return companies
