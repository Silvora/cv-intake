"use client"

import * as React from "react"

import { apiClient } from "@/api"
import { useAppStore, type UploadResultType } from "@/app/store/app"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface CvDetailResponse {
  success: boolean
  item: {
    id: string
    filename: string
    job_id: string
    job_name?: string
    file_path?: string
    md5?: string | null
    status: string
    error?: string | null
    ocr_engine?: string | null
    resume_text?: string | null
    resume_text_length?: number | null
    created_at?: string
    updated_at?: string
  }
}

function getStatusLabel(status: UploadResultType["status"]) {
  switch (status) {
    case "queued":
      return "已排队"
    case "uploading":
      return "上传中"
    case "processing":
      return "处理中"
    case "processed":
      return "已完成"
    case "ocr_no_text":
      return "无文本"
    case "skipped_duplicate_md5":
      return "重复"
    case "skipped_empty_file":
      return "空文件"
    case "skipped_non_pdf":
      return "非PDF"
    case "error":
      return "失败"
    default:
      return "待处理"
  }
}

function normalizeCvDetail(
  item: CvDetailResponse["item"]
): UploadResultType {
  const md5 = typeof item.md5 === "string" ? item.md5 : undefined
  const resultId = md5 || String(item.id)

  return {
    id: resultId,
    filename: String(item.filename ?? ""),
    job_id: String(item.job_id ?? ""),
    job_name: typeof item.job_name === "string" ? item.job_name : undefined,
    file_path:
      typeof item.file_path === "string" ? item.file_path : undefined,
    md5,
    status: String(item.status ?? "idle") as UploadResultType["status"],
    created_at:
      typeof item.created_at === "string" ? item.created_at : undefined,
    updated_at:
      typeof item.updated_at === "string" ? item.updated_at : undefined,
    ocr_engine:
      typeof item.ocr_engine === "string" ? item.ocr_engine : undefined,
    resume_text:
      typeof item.resume_text === "string" ? item.resume_text : undefined,
    resume_text_length:
      typeof item.resume_text_length === "number"
        ? item.resume_text_length
        : undefined,
    error: typeof item.error === "string" ? item.error : undefined,
  }
}

export default function PDFFolderViewer() {
  const uploadResults = useAppStore((state) => state.uploadResults)
  const selectedResultId = useAppStore((state) => state.selectedResultId)
  const mergeUploadResult = useAppStore((state) => state.mergeUploadResult)
  const apiBaseUrl = useAppStore((state) => state.userConfig.apiBaseUrl)

  const [isDetailLoading, setIsDetailLoading] = React.useState(false)
  const [detailError, setDetailError] = React.useState<string | null>(null)

  const results = React.useMemo(
    () =>
      Object.values(uploadResults).sort((a, b) =>
        (b.updated_at ?? b.created_at ?? "").localeCompare(
          a.updated_at ?? a.created_at ?? ""
        )
      ),
    [uploadResults]
  )

  const selectedResult =
    (selectedResultId ? uploadResults[selectedResultId] : null) ?? results[0]

  React.useEffect(() => {
    if (!selectedResult?.id) {
      return
    }

    let isMounted = true

    async function loadCvDetail() {
      try {
        setIsDetailLoading(true)
        setDetailError(null)
        const payload = await apiClient.get<CvDetailResponse>(
          `/cvs/${selectedResult.id}`
        )
        if (!isMounted || !payload.success) {
          return
        }

        mergeUploadResult(normalizeCvDetail(payload.item))
      } catch (error) {
        if (!isMounted) {
          return
        }
        setDetailError(
          error instanceof Error ? error.message : "获取简历详情失败"
        )
      } finally {
        if (isMounted) {
          setIsDetailLoading(false)
        }
      }
    }

    loadCvDetail()

    return () => {
      isMounted = false
    }
  }, [mergeUploadResult, selectedResult?.id])

  const pdfUrl =
    selectedResult?.file_path && apiBaseUrl
      ? new URL(selectedResult.file_path, apiBaseUrl).toString()
      : null

  if (!selectedResult) {
    return (
      <div className="flex min-h-full items-center justify-center rounded-xl border border-dashed bg-muted/10 p-10 text-muted-foreground">
        请选择一个已处理完成的 PDF。
      </div>
    )
  }

  return (
    <div className="grid h-full gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <Card className="min-h-0 overflow-hidden py-0">
        <CardContent className="h-[810px] py-4">
          {pdfUrl ? (
            <iframe
              title={selectedResult.filename}
              src={pdfUrl}
              className="h-full w-full border-0"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              当前简历没有可预览的 PDF 文件。
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="min-h-0 overflow-hidden py-0">
        <CardContent className="h-[810px] py-4">
          {detailError ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-destructive">
              {detailError}
            </div>
          ) : null}

          <ScrollArea className="h-full">
            <div className="grid gap-4 pr-3">
              <div className="rounded-lg border bg-muted/20 p-4">
                <pre className="whitespace-pre-wrap break-words text-xs leading-6">
                  {selectedResult.resume_text || "暂无提取文本"}
                </pre>
              </div>
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
