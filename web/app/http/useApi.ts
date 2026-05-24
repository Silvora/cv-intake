"use client"

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import * as React from "react"
import { toast } from "sonner"

import { apiClient } from "@/api"
import type {
  CvDetailResponse,
  CvResultsSsePayload,
  CvsResponse,
  JobApiItem,
  JobListType,
  JobsResponse,
  UploadFileInput,
  UploadResponse,
  UploadStatus
} from "./type"

function normalizeJob(item: JobApiItem): JobListType {
  return {
    id: String(item.id),
    label: item.label || "",
    description: item.description || "",
  }
}

/**
 * 岗位列表
 */
export function useJobsQuery() {
  return useQuery({
    queryKey: ["jobs"] as const,
    queryFn: async () => {
      const payload = await apiClient.get<JobsResponse>("/jobs")
      return payload.success ? payload.items.map(normalizeJob) : []
    },
    staleTime: 30_000,
  })
}


/**
 * 简历列表
 */
export function useCvsQuery() {
  return useQuery({
    queryKey: ["cvs"] as const,
    queryFn: async () => {
      const payload = await apiClient.get<CvsResponse>("/cvs")
      return payload.success ? payload.items : []
    },
    staleTime: 5_000,
  })
}


/**
 * 简历详情
 */
export function useCvDetailQuery(cvId?: string) {
  return useQuery({
    queryKey: ["cvs", cvId] as const,
    queryFn: async () => {
      if (!cvId) {
        return null
      }
      const payload = await apiClient.get<CvDetailResponse>(`/cvs/${cvId}`)
      return payload.success ? payload.item : null
    },
    enabled: Boolean(cvId),
    staleTime: 5_000,
  })
}

/**
 * 提交 PDF 上传，后端会异步跑 OCR 和工作流。
 */
export async function uploadCvs(args: {
  files: UploadFileInput[]
  jobId: string
}): Promise<UploadResponse> {
  const formData = new FormData()
  for (const item of args.files) {
    formData.append("files", item.file, item.name)
  }
  formData.append("job_ids", args.jobId)

  const payload = await apiClient.post<UploadResponse>("/upload", formData)
  return payload
}

/**
 * React Query 版本的上传动作。
 * 成功后会先把返回值写入简历列表缓存，等 SSE 再补充后续状态。
 */
export function useUploadCvsMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: uploadCvs,
    onSuccess: (payload) => {
      toast.success(`已提交 ${payload.count} 份 CV，正在异步处理中`)
      void queryClient.invalidateQueries({ queryKey: ["cvs"] })
    },
  })
}

/**
 * 保留给需要手工调用的场景。
 */
export function useApi() {
  return {
    uploadCvs,
    useJobsQuery,
    useCvsQuery,
    useCvDetailQuery,
    useUploadCvsMutation,
  }
}

/**
 * SSE 只负责结果推送，不掺杂组件逻辑。
 */
export function useApiSse(
  apiBaseUrl: string,
  onResults: (payload: CvResultsSsePayload) => void,
  onStatusChange?: (connected: boolean) => void
) {
  const onResultsRef = React.useRef(onResults)
  const onStatusChangeRef = React.useRef(onStatusChange)

  React.useEffect(() => {
    onResultsRef.current = onResults
  }, [onResults])

  React.useEffect(() => {
    onStatusChangeRef.current = onStatusChange
  }, [onStatusChange])

  React.useEffect(() => {
    if (!apiBaseUrl) return

    const url = new URL("/sse?type=results", apiBaseUrl)
    const source = new EventSource(url.toString())

    source.addEventListener("open", () => {
      onStatusChangeRef.current?.(true)
    })

    source.addEventListener("results", (event) => {
      const message = event as MessageEvent<string>
      try {
        const payload = JSON.parse(message.data) as CvResultsSsePayload
        onResultsRef.current(payload)
      } catch (error) {
        console.error("Failed to parse SSE payload", error)
      }
    })

    source.addEventListener("error", () => {
      onStatusChangeRef.current?.(false)
    })

    return () => {
      onStatusChangeRef.current?.(false)
      source.close()
    }
  }, [apiBaseUrl])
}

export type { UploadStatus }
