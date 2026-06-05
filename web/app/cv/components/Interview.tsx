"use client"

import * as React from "react"

import type { CvRecordApiItem } from "@/app/http/type"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SectionCard } from "./ListCard"

interface InterviewQuestionShape {
  category?: string
  question?: string
  answer?: string
  why_ask?: string
}

interface InterviewSectionShape {
  category?: string
  title?: string
  description?: string
  questions?: InterviewQuestionShape[]
}

interface InterviewResultShape {
  overall_summary?: string
  sections?: InterviewSectionShape[]
}

function getInterviewResultShape(
  value: Record<string, unknown> | null | undefined
): InterviewResultShape {
  if (!value || typeof value !== "object") {
    return {}
  }
  return value as InterviewResultShape
}

function getCategoryLabel(category?: string) {
  switch (category) {
    case "simple":
      return "基础题"
    case "senior":
      return "资深题"
    case "project":
      return "项目题"
    case "bonus":
      return "附加题"
    default:
      return "面试题"
  }
}

export function Interview({ selectedResult }: { selectedResult: CvRecordApiItem }) {
  const interviewResult = getInterviewResultShape(selectedResult.interview_result)
  const sections = interviewResult.sections ?? []
  const [activeQuestionId, setActiveQuestionId] = React.useState<string | null>(null)

  return (
    <div className="space-y-4">
      <SectionCard title="面试题总览" description="基于岗位与简历自动生成">
        <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm leading-6">
          {interviewResult.overall_summary || "暂无面试题摘要"}
        </div>
      </SectionCard>

      {sections.length ? (
        sections.map((section, sectionIndex) => (
          <SectionCard
            key={`${section.category ?? "section"}-${sectionIndex}`}
            title={section.title || getCategoryLabel(section.category)}
            description={section.description || getCategoryLabel(section.category)}
          >
            <div className="space-y-3">

              {(section.questions ?? []).length ? (
                <div className="space-y-3">
                  {section.questions?.map((question, questionIndex) => {
                    const questionId = `${section.category ?? "question"}-${questionIndex}`
                    const isActive = activeQuestionId === questionId

                    return (
                      <div
                        key={questionId}
                        className="rounded-lg border bg-muted/10"
                      >
                        <Button
                          variant="ghost"
                          className="h-auto w-full justify-between rounded-lg px-3 py-3 text-left"
                          onClick={() =>
                            setActiveQuestionId((current) =>
                              current === questionId ? null : questionId
                            )
                          }
                        >
                          <span className="min-w-0 whitespace-normal text-sm font-medium leading-6">
                            {questionIndex + 1}. {question.question || "暂无问题"}
                          </span>
                        </Button>

                        {isActive ? (
                          <div className="border-t px-3 py-3">
                            <div className="text-xs text-muted-foreground">
                              提问目的：{question.why_ask || "暂无"}
                            </div>
                            <div className="mt-3 rounded-md bg-background/80 px-3 py-2 text-sm leading-6">
                              <div className="mb-1 text-xs font-medium text-muted-foreground">
                                参考答案
                              </div>
                              {question.answer || "暂无答案"}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">暂无题目</div>
              )}
            </div>
          </SectionCard>
        ))
      ) : (
        <SectionCard title="面试题">
          <div className="text-sm text-muted-foreground">暂无面试题内容</div>
        </SectionCard>
      )}
    </div>
  )
}
