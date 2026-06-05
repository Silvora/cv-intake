"use client"

import { useCvDetailQuery } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
import { getProcessingStageWithAttempt, getStatusLabel } from "@/app/utils/status"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useParams } from "next/navigation"
import { useState } from "react"
import { Base } from "../components/Base"
import { Conclusion } from "../components/Conclusion"
import { Interview } from "../components/Interview"


export default function CVDetailPage() {
  const params = useParams<{ id: string }>()
  const cvId = Array.isArray(params?.id) ? params.id[0] : params?.id

  const [tab, setTab] = useState("base")
  const cvQuery = useCvDetailQuery(cvId)
  const apiBaseUrl = useAppStore((state) => state.userConfig.apiBaseUrl)
  const selectedResult = cvQuery.data ?? null

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
        <CardContent className="h-full py-4 ">
          {cvQuery.error ? (
            <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-destructive">
              获取详情失败
            </div>
          ) : null}

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge variant="outline">{getStatusLabel(selectedResult.status)}</Badge>
            {selectedResult.status === "processing" ? (
              <Badge variant="secondary">
                {getProcessingStageWithAttempt(
                  selectedResult.processing_stage,
                  selectedResult.processing_attempt
                )}
              </Badge>
            ) : null}
          </div>

          <Tabs value={tab} onValueChange={setTab} className="h-full">
            <TabsList className="w-full justify-between min-h-[30px] h-[30px] max-h-[30px]">
              <TabsTrigger value="base">基本信息</TabsTrigger>
              <TabsTrigger value="verify">结论</TabsTrigger>
              <TabsTrigger value="interview">面试题</TabsTrigger>
            </TabsList>

            <ScrollArea className="h-[calc(100%-36px)]" hideScrollbar viewportClassName="scrollbar-hide">
              <TabsContent value="base" className="space-y-4 m-0.5">
                <Base selectedResult={selectedResult} />
              </TabsContent>

              <TabsContent value="verify" className="space-y-4 m-0.5">
                <Conclusion selectedResult={selectedResult} />
              </TabsContent>

              <TabsContent value="interview" className="space-y-4 m-0.5">
                <Interview selectedResult={selectedResult} />
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
