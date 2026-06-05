"use client"

import * as React from "react"

import type { CvRecordApiItem } from "@/app/http/type"
import { useApiSse, useReactQueryClient } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"

export function useCVUploadSSE(apiBaseUrl: string) {
  const queryClient = useReactQueryClient()
  const setSSEConnected = useAppStore((state) => state.setSSEConnected)

  const handleResults = React.useCallback(
    (payload: Record<string, CvRecordApiItem>) => {
      for (const [id, item] of Object.entries(payload)) {
        queryClient.setQueryData(["cvs", id], item)
      }

      queryClient.setQueryData(["cvs"], (current: CvRecordApiItem[] | undefined) => {
        const nextMap = new Map((current ?? []).map((item) => [item.id, item]))

        for (const [id, item] of Object.entries(payload)) {
          if (item.status === "deleted") {
            nextMap.delete(id)
            continue
          }
          nextMap.set(id, {
            ...nextMap.get(id),
            ...item,
          })
        }

        return Array.from(nextMap.values()).sort((a, b) =>
          String(b.updated_at ?? "").localeCompare(String(a.updated_at ?? ""))
        )
      })

      const activeCvId = window.location.pathname.startsWith("/cv/")
        ? window.location.pathname.split("/")[2]
        : null

      if (activeCvId && payload[activeCvId]) {
        queryClient.setQueryData(["cvs", activeCvId], {
          ...(queryClient.getQueryData(["cvs", activeCvId]) as CvRecordApiItem | undefined),
          ...payload[activeCvId],
        })
      }
    },
    [queryClient]
  )

  useApiSse(apiBaseUrl, handleResults, setSSEConnected)
}
