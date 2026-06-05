"use client"

import * as React from "react"

import type { CvRecordApiItem } from "@/app/http/type"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SectionCard } from "./ListCard"

interface SearchEvidenceShape {
  title?: string
  snippet?: string | null
  link?: string | null
}

interface CompanyVerificationShape {
  company?: string
  verified?: boolean | null
  profile?: string | null
  business_scope?: string | null
  representative_projects?: string[]
  reason?: string | null
  evidence?: SearchEvidenceShape[]
}

interface VerifyResultShape {
  verification_summary?: string
  companies?: CompanyVerificationShape[]
}

interface ScoreResultShape {
  reason?: {
    why_this_score?: string
    risk_points?: string[]
    missing_requirements?: string[]
  }
  improvement_suggestions?: string[]
}

function getVerifyResultShape(
  value: Record<string, unknown> | null | undefined
): VerifyResultShape {
  if (!value || typeof value !== "object") {
    return {}
  }

  return value as VerifyResultShape
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
  label?: string
  value?: React.ReactNode
}) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm">
      {label ? <span className="pr-1 font-bold">{label}: </span> : null}
      <span className="wrap-break-word text-foreground">{value ?? "暂无"}</span>
    </div>
  )
}

export function Conclusion({ selectedResult }: { selectedResult: CvRecordApiItem }) {
  const verifyResult = getVerifyResultShape(selectedResult.verify_result)
  const scoreResult = getScoreResultShape(selectedResult.score_result)
  const legacyScore = selectedResult.data?.result?.score
  const [activeCompanyKey, setActiveCompanyKey] = React.useState<string | null>(null)
  const improvementSuggestions =
    scoreResult.improvement_suggestions ?? legacyScore?.improvement_suggestions ?? []
  const missingRequirements =
    scoreResult?.reason?.missing_requirements ?? scoreResult?.reason?.missing_requirements ?? []

  return (
    <div className="space-y-4">
      <SectionCard title="核验结论" description="公司基础信息核验">
        <div className="space-y-3 text-sm">
          <KeyValueRow value={verifyResult.verification_summary} />
        </div>
      </SectionCard>

      <SectionCard title="公司核验" description="只校验公司简介、主营业务和代表产品/项目">
        {verifyResult.companies?.length ? (
          <div className="space-y-3">
            {verifyResult.companies.map((company, index) => {
              const companyKey = `${company.company ?? "company"}-${index}`
              const isActive = activeCompanyKey === companyKey
              const summaryText =
                company.profile ||
                company.business_scope ||
                company.reason ||
                "暂无公司基础信息摘要"

              return (
                <div key={companyKey} className="rounded-lg border bg-muted/10">
                  <Button
                    variant="ghost"
                    className="h-auto w-full justify-between rounded-lg px-3 py-3 text-left"
                    onClick={() =>
                      setActiveCompanyKey((current) =>
                        current === companyKey ? null : companyKey
                      )
                    }
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium">{company.company || "未命名公司"}</div>
                        <Badge
                          variant={
                            company.verified === true
                              ? "secondary"
                              : company.verified === false
                                ? "destructive"
                                : "outline"
                          }
                        >
                          {company.verified === true
                            ? "已核验"
                            : company.verified === false
                              ? "核验异常"
                              : "待确认"}
                        </Badge>
                      </div>
                      <div className="mt-1 truncate text-xs text-muted-foreground">
                        {summaryText}
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {isActive ? "收起" : "展开"}
                    </span>
                  </Button>

                  {isActive ? (
                    <div className="space-y-3 border-t px-3 py-3">
                      <div className="space-y-2 text-sm">
                        <KeyValueRow value={company.profile || "暂无公司简介"} />
                        <KeyValueRow value={company.business_scope || "暂无主营业务信息"} />
                        <KeyValueRow
                          value={
                            company.representative_projects?.length
                              ? company.representative_projects.join("；")
                              : "暂无代表产品或项目"
                          }
                        />
                        {company.reason ? <KeyValueRow value={company.reason} /> : null}
                      </div>

                      {company.evidence?.length ? (
                        <div className="space-y-2">
                          {company.evidence.map((evidence, evidenceIndex) => (
                            <div
                              key={`${company.company ?? "company"}-evidence-${evidenceIndex}`}
                              className="rounded-md border bg-background/70 px-3 py-2 text-xs leading-6"
                            >
                              <div className="font-medium">{evidence.title || "未命名来源"}</div>
                              {evidence.snippet ? (
                                <div className="mt-1 text-muted-foreground">{evidence.snippet}</div>
                              ) : null}
                              {evidence.link ? (
                                <a
                                  href={evidence.link}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="mt-1 inline-block text-primary underline underline-offset-4"
                                >
                                  查看来源
                                </a>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">暂无公司核验内容</div>
        )}
      </SectionCard>

      <SectionCard title="招聘风险">
        <ul className="space-y-2 text-sm">
          {missingRequirements ? (
            missingRequirements.map((item, index) => (
              <li
                key={index}
                className="rounded-md border bg-muted/20 px-3 py-2 leading-6"
              >
               {index+1}. {item}
              </li>
            ))
          ) : (
            <li className="text-muted-foreground">暂无</li>
          )}
        </ul>
      </SectionCard>

      <SectionCard title="改进建议">
        <ul className="space-y-2 text-sm">
          {improvementSuggestions.length ? (
            improvementSuggestions.map((item, index) => (
              <li
                key={index}
                className="rounded-md border bg-muted/20 px-3 py-2 leading-6"
              >
               {index+1}. {item}
              </li>
            ))
          ) : (
            <li className="text-muted-foreground">暂无</li>
          )}
        </ul>
      </SectionCard>
    </div>
  )
}
