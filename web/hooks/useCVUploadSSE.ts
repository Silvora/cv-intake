"use client"

import * as React from "react"

import type { CvRecordApiItem } from "@/app/http/type"
import { useApiSse } from "@/app/http/useApi"

function normalizeUploadResult(
  id: string,
  result: CvRecordApiItem
): void {
  void id
  void result
}

export function useCVUploadSSE(apiBaseUrl: string) {
  const handleResults = React.useCallback(
    (payload: Record<string, CvRecordApiItem>) => {
      for (const [id, item] of Object.entries(payload)) {
        normalizeUploadResult(id, item)
      }
    },
    []
  )

  useApiSse(apiBaseUrl, handleResults)
}
