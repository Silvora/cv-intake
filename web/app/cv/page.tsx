"use client"

import { useRouter } from "next/navigation"

import { useCvsQuery } from "@/app/http/useApi"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

function getStatusLabel(status: string) {
  switch (status) {
    case "processed":
      return "已完成"
    case "processing":
      return "处理中"
    case "queued":
      return "已排队"
    case "uploading":
      return "上传中"
    case "error":
      return "失败"
    default:
      return status || "未知"
  }
}

export default function CVPage() {
  const router = useRouter()
  const cvsQuery = useCvsQuery()

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">简历列表</h1>
        <p className="text-sm text-muted-foreground">点击任意一条记录进入详情页。</p>
      </div>

      {cvsQuery.isLoading ? (
        <div className="rounded-lg border bg-muted/20 p-4 text-sm text-muted-foreground">
          正在加载简历列表...
        </div>
      ) : cvsQuery.error ? (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          获取简历列表失败
        </div>
      ) : cvsQuery.data?.length ? (
        <div className="grid gap-3">
          {cvsQuery.data.map((item) => (
            <Card
              key={item.id}
              className="cursor-pointer border-border/60 transition-colors hover:bg-muted/30"
              onClick={() => router.push(`/cv/${item.id}`)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">{item.filename}</CardTitle>
                  <Badge variant="outline">{getStatusLabel(item.status)}</Badge>
                </div>
                <CardDescription>{item.job_name || item.job_id}</CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {item.updated_at || item.created_at || "暂无时间"}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed bg-muted/10 p-10 text-center text-sm text-muted-foreground">
          暂无简历记录，请先上传 PDF。
        </div>
      )}
    </div>
  )
}
