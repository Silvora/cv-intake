"use client"

import * as React from "react"

import type { CvRecordApiItem } from "@/app/http/type"
import { getOverallScore, getScoreItemTone, getScoreTone } from "@/app/utils/status"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Label,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  RadialBar,
  RadialBarChart,
} from "recharts"
import { ListCard, SectionCard } from "./ListCard"

interface ResumeInfoShape {
  name?: string
  phone?: string
  email?: string
  location?: string
  school?: string
  current_job_title?: string
  desired_job_title?: string
  summary?: string
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
  project_name?: string
  start_date?: string
  end_date?: string
}

interface SkillItemShape {
  name?: string
  level?: string
}

interface ResumeSummaryShape {
  education?: EducationItemShape[]
  work_experiences?: WorkExperienceItemShape[]
  skills?: SkillItemShape[]
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
}

function getScoreAccentColor(score?: number | null) {
  if (typeof score !== "number") return "#94a3b8"
  if (score <= 30) return "#e11d48"
  if (score <= 60) return "#d97706"
  if (score <= 90) return "#0284c7"
  return "#059669"
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

function KeyValueRow({
  label,
  value,
}: {
  label: string
  value?: React.ReactNode
}) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm">
      <span className="pr-1 font-bold">{label}: </span>
      <span className="wrap-break-word text-foreground">{value ?? "暂无"}</span>
    </div>
  )
}

function ClickableValueRow({
  label,
  value,
  dialogTitle,
  dialogDescription,
  dialogContent,
}: {
  label: string
  value?: React.ReactNode
  dialogTitle: string
  dialogDescription?: string
  dialogContent: React.ReactNode
}) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm">
      <span className="pr-1 font-bold">{label}: </span>
      <Dialog>
        <DialogTrigger
          render={
            <Button variant="link" size="sm" className="h-auto px-0 py-0 text-sm wrap-break-word text-foreground">
              {value ?? "暂无"}
            </Button>
          }
        />
        <DialogContent className="max-w-3xl min-w-2xl">
          <DialogHeader>
            <DialogTitle>{dialogTitle}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-y-auto rounded-lg border bg-muted/20 p-4">
            {dialogContent}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

const radarChartConfig = {
  value: {
    label: "分项分数",
    color: "#0284c7",
  },
} satisfies ChartConfig

export function Base({ selectedResult }: { selectedResult: CvRecordApiItem }) {
  const resumeSummary = getResumeSummaryShape(selectedResult.resume_summary)
  const scoreResult = getScoreResultShape(selectedResult.score_result)
  const legacyInfo = selectedResult.data?.result?.info
  const legacyScore = selectedResult.data?.result?.score
  const scoreReason =
    (selectedResult.score_result as
      | { reason?: { why_this_score?: string } }
      | null
      | undefined)?.reason?.why_this_score ??
    selectedResult.data?.result?.score?.reason?.why_this_score

  const overallScore =
    getOverallScore(selectedResult) ?? legacyScore?.score?.overall ?? null
  const scoreTone = getScoreTone(overallScore ?? undefined)
  const scoreAccentColor = getScoreAccentColor(overallScore)
  const radialChartConfig = {
    score: {
      label: "得分",
      color: scoreAccentColor,
    },
  } satisfies ChartConfig
  const currentJobLabel =
    selectedResult.job_name ||
    selectedResult.job_id ||
    resumeSummary.user?.desired_job_title ||
    "暂无岗位信息"

  const scoreBreakdown = {
    must_have_match:
      scoreResult.score?.must_have_match ?? legacyScore?.score?.must_have_match ?? null,
    experience_match:
      scoreResult.score?.experience_match ?? legacyScore?.score?.experience_match ?? null,
    skill_match:
      scoreResult.score?.skill_match ?? legacyScore?.score?.skill_match ?? null,
    education_match:
      scoreResult.score?.education_match ?? legacyScore?.score?.education_match ?? null,
  }

  const radialData = [
    {
      metric: "score",
      value: typeof overallScore === "number" ? overallScore : 0,
      fill: "var(--color-score)",
    },
  ]

  const radarData = [
    {
      metric: "硬性要求",
      value: typeof scoreBreakdown.must_have_match === "number" ? scoreBreakdown.must_have_match : 0,
    },
    {
      metric: "经验匹配",
      value: typeof scoreBreakdown.experience_match === "number" ? scoreBreakdown.experience_match : 0,
    },
    {
      metric: "技能匹配",
      value: typeof scoreBreakdown.skill_match === "number" ? scoreBreakdown.skill_match : 0,
    },
    {
      metric: "教育匹配",
      value: typeof scoreBreakdown.education_match === "number" ? scoreBreakdown.education_match : 0,
    },
  ]

  return (
    <div className="space-y-4">
      <SectionCard title="评分概览" description="总分与分项评分可视化">
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-xl border bg-muted/10 p-4">
            <div
              className="mb-3 text-sm font-medium"
            >
              {radialChartConfig.score.label}
            </div>
            <div className="mx-auto size-52">
              <ChartContainer
                config={radialChartConfig}
                className="aspect-square h-full! w-full!"
              >
                <RadialBarChart
                  data={radialData}
                  startAngle={90}
                  endAngle={-270}
                  innerRadius="58%"
                  outerRadius="78%"
                >
                  <PolarAngleAxis
                    type="number"
                    domain={[0, 100]}
                    tick={false}
                  />
                  <ChartTooltip
                    content={<ChartTooltipContent nameKey="metric" hideLabel />}
                  />
                  <PolarGrid
                    gridType="circle"
                    radialLines={false}
                    stroke="none"
                    polarRadius={[80, 66]}
                  />
                  <PolarRadiusAxis tick={false} tickLine={false} axisLine={false}>
                    <Label
                      content={({ viewBox }) => {
                        if (!viewBox || !("cx" in viewBox) || !("cy" in viewBox)) {
                          return null
                        }

                        return (
                          <text
                            x={viewBox.cx}
                            y={viewBox.cy}
                            textAnchor="middle"
                            dominantBaseline="middle"
                          >
                            <tspan
                              x={viewBox.cx}
                              y={viewBox.cy - 6}
                              className="text-3xl font-semibold"
                              fill={scoreAccentColor}
                            >
                              {typeof overallScore === "number" ? overallScore : "--"}
                            </tspan>
                            <tspan
                              x={viewBox.cx}
                              y={viewBox.cy + 20}
                              className="fill-muted-foreground text-xs"
                            >
                              总分 / 100
                            </tspan>
                          </text>
                        )
                      }}
                    />
                  </PolarRadiusAxis>
                  <RadialBar
                    dataKey="value"
                    background={{ fill: "rgba(148, 163, 184, 0.18)" }}
                    cornerRadius={999}
                  />
                </RadialBarChart>
              </ChartContainer>
            </div>
            <div className="flex justify-center h-30 ">
              <div className={`w-full h-full overflow-y-auto scrollbar-hide rounded-xl p-2 text-xs leading-6 border ${scoreTone}`}>
                {scoreReason || "暂无评分原因"}
              </div>
            </div>
          </div>

          <div className="rounded-xl border bg-muted/10 p-4">
            <div className="mb-3 text-sm font-medium">分项评分</div>
            <ChartContainer config={radarChartConfig} className="h-56 w-full">
              <RadarChart data={radarData} outerRadius="72%">
                <ChartTooltip content={<ChartTooltipContent nameKey="metric" />} />
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis axisLine={false} tick={false} domain={[0, 100]} />
                <Radar
                  dataKey="value"
                  stroke="var(--color-value)"
                  fill="var(--color-value)"
                  fillOpacity={0.2}
                />
              </RadarChart>
            </ChartContainer>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              {[
                ["硬性要求", scoreBreakdown.must_have_match],
                ["经验匹配", scoreBreakdown.experience_match],
                ["技能匹配", scoreBreakdown.skill_match],
                ["教育匹配", scoreBreakdown.education_match],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm ring-1 whitespace-nowrap ${getScoreItemTone(
                    typeof value === "number" ? value : null
                  )}`}
                >
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="text-xl font-semibold leading-none">
                    {typeof value === "number" ? value : "--"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="基础信息" description="结构化简历抽取结果">
        <div className="space-y-2 text-sm">
             <ClickableValueRow
            label="期望职位"
            value={resumeSummary.user?.desired_job_title ?? currentJobLabel}
            dialogTitle={currentJobLabel}
            dialogDescription="点击期望职位后可查看当前 CV 绑定的岗位与 JD。"
            dialogContent={
              
                  <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-foreground">
                    {selectedResult.job_text || "暂无岗位描述"}
                  </pre>
            }
          />
          <KeyValueRow label="姓名" value={resumeSummary.user?.name ?? legacyInfo?.name} />
          <KeyValueRow label="电话" value={resumeSummary.user?.phone ?? legacyInfo?.phone} />
          <KeyValueRow label="邮箱" value={resumeSummary.user?.email ?? legacyInfo?.email} />
          {/* <KeyValueRow
            label="位置"
            value={resumeSummary.user?.location ?? legacyInfo?.location}
          /> */}
          <KeyValueRow label="学校" value={resumeSummary.user?.school} />
          {/* <KeyValueRow label="当前职位" value={resumeSummary.user?.current_job_title} /> */}
          <KeyValueRow label="个人简介" value={resumeSummary.user?.summary ?? legacyInfo?.summary} />
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
              [item.company, item.title, item.project_name, item.start_date, item.end_date]
                .filter(Boolean)
                .join(" · ")
            )
            .filter((item): item is string => Boolean(item)) ?? []
        }
      />

      <SectionCard title="技能">
        {resumeSummary.skills?.length ? (
          <div className="flex flex-wrap gap-2">
            {resumeSummary.skills.map((item, index) => (
              <Badge key={`${item.name ?? "skill"}-${index}`} variant="outline" className="h-auto px-3 py-1 text-xs">
                {[item.name, item.level].filter(Boolean).join(" · ")}
              </Badge>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">暂无</div>
        )}
      </SectionCard>
    </div>
  )
}
