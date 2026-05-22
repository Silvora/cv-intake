"use client"

import * as React from "react"

import { useAppStore, type UploadResultType } from "@/app/store/app"

function normalizeUploadResult(
  id: string,
  result: Record<string, unknown>
): UploadResultType {
  const md5 = typeof result.md5 === "string" ? result.md5 : undefined
  const resultId = md5 || id
  const data =
    result.data && typeof result.data === "object"
      ? (result.data as UploadResultType["data"])
      : undefined
  const errorCode = data?.error?.code
  const normalizedStatus =
    errorCode === "ocr_no_text"
      ? "ocr_no_text"
      : (String(result.status ?? "idle") as UploadResultType["status"])

  return {
    id: resultId,
    filename: String(result.filename ?? ""),
    job_id: String(result.job_id ?? ""),
    job_name:
      typeof result.job_name === "string" ? result.job_name : undefined,
    file_path:
      typeof result.file_path === "string" ? result.file_path : undefined,
    md5,
    status: normalizedStatus,
    created_at:
      typeof result.created_at === "string" ? result.created_at : undefined,
    updated_at:
      typeof result.updated_at === "string" ? result.updated_at : undefined,
    ocr_engine:
      typeof result.ocr_engine === "string" ? result.ocr_engine : undefined,
    resume_text:
      typeof result.resume_text === "string" ? result.resume_text : undefined,
    resume_text_length:
      typeof result.resume_text_length === "number"
        ? result.resume_text_length
        : undefined,
    jd_text_length:
      typeof result.jd_text_length === "number"
        ? result.jd_text_length
        : undefined,
    error: typeof result.error === "string" ? result.error : undefined,
    data,
  }
}

export function useCVUploadSSE() {
  const apiBaseUrl = useAppStore((state) => state.userConfig.apiBaseUrl)
  const mergeUploadResults = useAppStore((state) => state.mergeUploadResults)
  const setSSEConnected = useAppStore((state) => state.setSSEConnected)

  React.useEffect(() => {
    if (!apiBaseUrl) {
      return
    }

    const url = new URL("/sse?type=results", apiBaseUrl)
    const source = new EventSource(url.toString())

    source.addEventListener("open", () => {
      setSSEConnected(true)
    })

    source.addEventListener("results", (event) => {
      const message = event as MessageEvent<string>

      try {
        const payload = JSON.parse(message.data) as Record<
          string,
          Record<string, unknown>
        >

        const nextResults: Record<string, UploadResultType> = {}
        for (const [id, item] of Object.entries(payload)) {
          nextResults[id] = normalizeUploadResult(id, item)
        }

        mergeUploadResults(nextResults)
      } catch (error) {
        console.error("Failed to parse SSE payload", error)
      }
    })

    source.addEventListener("error", () => {
      setSSEConnected(false)
    })

    return () => {
      setSSEConnected(false)
      source.close()
    }
  }, [apiBaseUrl, mergeUploadResults, setSSEConnected])
}
