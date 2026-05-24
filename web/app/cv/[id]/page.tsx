"use client"

import { useCvDetailQuery } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
import {
    getScoreItemTone,
    getScoreTone
} from "@/app/utils/status"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useParams } from "next/navigation"
import { useState, type ReactNode } from "react"
import { ListCard, SectionCard } from "../components/ListCard"
interface ResumeInfoShape {
  name?: string
  phone?: string
  email?: string
  location?: string
}

interface EducationItemShape {
  school?: string
  degree?: string
  start_date?: string
  end_date?: string
}

interface WorkExperienceItemShape {
  company?: string
  title?: string
  start_date?: string
  end_date?: string
}

interface ResumeSummaryShape {
  education?: EducationItemShape[]
  work_experiences?: WorkExperienceItemShape[]
  user?: ResumeInfoShape
}

interface ScoreBreakdownShape {
  overall?: number
  must_have_match?: number
  experience_match?: number
  skill_match?: number
  education_match?: number
}

interface ScoreResultShape {
  score?: ScoreBreakdownShape
  reason?: {
    why_this_score?: string
    met_requirements?: string[]
    missing_requirements?: string[]
    risk_points?: string[]
  }
  improvement_suggestions?: string[]
}

interface VerifyResultShape {
  overall_status?: string
  verification_summary?: string
}

function getResumeSummaryShape(
  value: Record<string, unknown> | null | undefined
): ResumeSummaryShape {
  if (!value || typeof value !== "object") {
    return {}
  }

  return value as ResumeSummaryShape
}

function getScoreResultShape(
  value: Record<string, unknown> | null | undefined
): ScoreResultShape {
  if (!value || typeof value !== "object") {
    return {}
  }

  return value as ScoreResultShape
}

function getVerifyResultShape(
  value: Record<string, unknown> | null | undefined
): VerifyResultShape {
  if (!value || typeof value !== "object") {
    return {}
  }

  return value as VerifyResultShape
}

function KeyValueRow({
  label,
  value,
}: {
  label: string
  value?: ReactNode
}) {
  return (
    <div className="items-start gap-3 rounded-md border bg-muted/20 px-3 py-2 text-sm">
      <span className="min-w-16 shrink-0 font-bold pr-1">{label}: </span>
      <span className="min-w-0 flex-1 wrap-break-word text-foreground">
        {value ?? "暂无"}
      </span>
    </div>
  )
}


export default function CVDetailPage() {
  const params = useParams<{ id: string }>()
  const cvId = Array.isArray(params?.id) ? params.id[0] : params?.id

  const [tab, setTab] = useState("summary")
  const cvQuery = useCvDetailQuery(cvId)
  const apiBaseUrl = useAppStore((state) => state.userConfig.apiBaseUrl)
  const selectedResult = cvQuery.data ?? null
  const resumeSummary = getResumeSummaryShape(selectedResult?.resume_summary)
  const verifyResult = getVerifyResultShape(selectedResult?.verify_result)
  const scoreResult = getScoreResultShape(selectedResult?.score_result)
  const legacyInfo = selectedResult?.data?.result?.info
  const legacyScore = selectedResult?.data?.result?.score
  const overallScore = scoreResult.score?.overall ?? legacyScore?.score?.overall ?? null
  const scoreTone = getScoreTone(overallScore ?? undefined)
  const improvementSuggestions =
    scoreResult.improvement_suggestions ?? legacyScore?.improvement_suggestions ?? []

  const pdfUrl = selectedResult?.file_path
    ? new URL(selectedResult.file_path, apiBaseUrl).toString()
    : null

  if (!selectedResult) {
    return (
      <div className="flex min-h-full items-center justify-center rounded-xl border border-dashed bg-muted/10 p-10 text-muted-foreground">
        {cvQuery.isLoading ? "正在加载简历详情..." : "未找到该简历。"}
      </div>
    )
  }

  return (
    <div className="grid h-[calc(100vh-96px)] overflow-hidden gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
      <Card className="min-h-0 overflow-hidden border-border/60 py-0 m-0.5">
        <CardContent className="h-full py-4 ">
          {pdfUrl ? (
            <iframe title={selectedResult.filename} src={pdfUrl} className="h-full w-full border-0" />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              当前简历没有可预览的 PDF 文件。
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="min-h-0 overflow-hidden border-border/60 py-0 m-0.5">
        <CardContent className="h-full py-4">
          {cvQuery.error ? (
            <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-destructive">
              获取详情失败
            </div>
          ) : null}

          <Tabs value={tab} onValueChange={setTab} className="h-full">
            <TabsList className="w-full justify-between">
              <TabsTrigger value="summary">摘要</TabsTrigger>
              <TabsTrigger value="verify">核验</TabsTrigger>
              <TabsTrigger value="score">评分</TabsTrigger>
              <TabsTrigger value="text">原文</TabsTrigger>
            </TabsList>

            <ScrollArea className="h-162.5" hideScrollbar viewportClassName="scrollbar-hide">
              <TabsContent value="summary" className="space-y-4 m-0.5">
                <SectionCard title="基础信息" description="结构化简历抽取结果">
                  <div className="space-y-1 text-sm">
                    <KeyValueRow
                      label="姓名"
                      value={resumeSummary.user?.name ?? legacyInfo?.name}
                    />
                    <KeyValueRow
                      label="电话"
                      value={resumeSummary.user?.phone ?? legacyInfo?.phone}
                    />
                    <KeyValueRow
                      label="邮箱"
                      value={resumeSummary.user?.email ?? legacyInfo?.email}
                    />
                    <KeyValueRow
                      label="位置"
                      value={resumeSummary.user?.location ?? legacyInfo?.location}
                    />
                  </div>
                </SectionCard>

                <ListCard
                  title="教育经历"
                  items={
                    resumeSummary.education
                      ?.map((item) =>
                        [item.school, item.degree, item.start_date, item.end_date]
                          .filter(Boolean)
                          .join(" · ")
                      )
                      .filter((item): item is string => Boolean(item)) ?? []
                  }
                />

                <ListCard
                  title="工作经历"
                  items={
                    resumeSummary.work_experiences
                      ?.map((item) =>
                        [item.company, item.title, item.start_date, item.end_date]
                          .filter(Boolean)
                          .join(" · ")
                      )
                      .filter((item): item is string => Boolean(item)) ?? []
                  }
                />
              </TabsContent>

              <TabsContent value="verify" className="space-y-4 m-0.5">
                <SectionCard title="核验结论" description="学校、公司与工作时间核验">
                  <div className="space-y-3 text-sm">
                    <KeyValueRow
                      label="结论"
                      value={verifyResult.verification_summary}
                    />
                  </div>
                </SectionCard>

                <SectionCard title="评分原因" description="核验结果会影响评分">
                  <div className="space-y-2 text-sm">
                    <KeyValueRow
                      label="原因"
                      value={scoreResult.reason?.why_this_score}
                    />
                    <KeyValueRow
                      label="风险"
                      value={scoreResult.reason?.risk_points?.join("；")}
                    />
                  </div>
                </SectionCard>
              </TabsContent>

              <TabsContent value="score" className="space-y-4 m-0.5">
                <SectionCard title="评分总览" description="总分与分项评分">
                  <div className="grid gap-4 lg:grid-cols-[100px_minmax(0,1fr)]">
                    <div className="flex h-full items-center gap-3 rounded-xl border bg-muted/10 lg:flex-col lg:items-start lg:justify-center">
                      <div
                        className={`flex h-full w-full items-center justify-center rounded-xl text-3xl font-semibold ring-1 ${scoreTone}`}
                      >
                        {overallScore ?? "?"}
                        <span className="text-sm">分</span>
                      </div>
                    </div>

                    <div className="grid h-full gap-3 sm:grid-cols-2">
                      {[
                        ["硬性要求", scoreResult.score?.must_have_match],
                        ["经验匹配", scoreResult.score?.experience_match],
                        ["技能匹配", scoreResult.score?.skill_match],
                        ["教育匹配", scoreResult.score?.education_match],
                      ].map(([label, value]) => (
                        <div
                          key={label as string}
                          className={`flex items-center rounded-lg border p-3 ${getScoreItemTone(
                            typeof value === "number" ? value : null
                          )}`}
                        >
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">
                              {label as string}
                            </div>
                            <div className="text-2xl font-semibold leading-none">
                              {typeof value === "number" ? value : "暂无"}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </SectionCard>

                <SectionCard title="改进建议">
                  <ul className="space-y-2 text-sm">
                    {improvementSuggestions.length ? (
                      improvementSuggestions.map((item, index) => (
                        <li key={index} className="rounded-md border bg-muted/20 px-3 py-2 leading-6">
                          {item}
                        </li>
                      ))
                    ) : (
                      <li className="text-muted-foreground">暂无</li>
                    )}
                  </ul>
                </SectionCard>
              </TabsContent>

              <TabsContent value="text" className="space-y-4 m-0.5">
                <SectionCard title="岗位描述">
                  <pre className="whitespace-pre-wrap wrap-break-word rounded-md bg-muted/30 p-3 text-xs leading-6">
                    {selectedResult.job_text || "暂无岗位描述"}
                  </pre>
                </SectionCard>

                <SectionCard title="OCR 原文">
                  <pre className="whitespace-pre-wrap wrap-break-word rounded-md bg-muted/30 p-3 text-xs leading-6">
                    {selectedResult.resume_text || "暂无提取文本"}
                  </pre>
                </SectionCard>
              </TabsContent>
            </ScrollArea>
          </Tabs>

          <Separator className="my-4" />

          <div className="text-xs text-muted-foreground">
            {selectedResult.final_answer || "暂无最终结论"}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
