"use client"

import * as React from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInput,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import { Activity01Icon, PdfIcon, RubberDuckIcon } from "@hugeicons/core-free-icons"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/api"
import { SettingsDialog } from "./settings-dialog"
import { UploadsDialog } from "./uploads-dialog"
import { useAppStore, type UploadResultType } from "@/app/store/app"
import { useCVUploadSSE } from "@/hooks/useCVUploadSSE"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type IconSvgObject =
  | [
      string,
      {
        [key: string]: string | number
      },
    ][]
  | readonly (readonly [
      string,
      {
        readonly [key: string]: string | number
      },
    ])[]

interface navType {
  title: string
  url: string
  icon: IconSvgObject
  isActive: boolean
}

const navMain: navType[] = [
  {
    title: "CV",
    url: "cv",
    icon: PdfIcon,
    isActive: true,
  },
]

interface CvsResponse {
  success: boolean
  items: Array<{
    id: string
    filename: string
    job_id: string
    job_name?: string
    file_path?: string
    md5?: string | null
    status: string
    error?: string | null
    ocr_engine?: string | null
    resume_text_length?: number | null
    created_at?: string
    updated_at?: string
  }>
  total: number
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

function getStatusClassName(status: UploadResultType["status"]) {
  switch (status) {
    case "processed":
      return "bg-emerald-500/12 text-emerald-700 ring-emerald-500/20"
    case "processing":
    case "uploading":
      return "bg-sky-500/12 text-sky-700 ring-sky-500/20"
    case "queued":
      return "bg-slate-500/12 text-slate-700 ring-slate-500/20"
    case "ocr_no_text":
      return "bg-amber-500/12 text-amber-700 ring-amber-500/20"
    case "skipped_duplicate_md5":
      return "bg-orange-500/12 text-orange-700 ring-orange-500/20"
    case "skipped_empty_file":
    case "skipped_non_pdf":
    case "error":
      return "bg-rose-500/12 text-rose-700 ring-rose-500/20"
    default:
      return "bg-slate-500/12 text-slate-700 ring-slate-500/20"
  }
}

function normalizeCvResult(
  item: CvsResponse["items"][number]
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
    resume_text_length:
      typeof item.resume_text_length === "number"
        ? item.resume_text_length
        : undefined,
    error: typeof item.error === "string" ? item.error : undefined,
  }
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  useCVUploadSSE()

  const [activeItem, setActiveItem] = React.useState(navMain[0])
  const [isResultsLoading, setIsResultsLoading] = React.useState(false)
  const [resultsLoadError, setResultsLoadError] = React.useState<string | null>(null)
  const { setOpen } = useSidebar()
  const router = useRouter()
  const uploadResults = useAppStore((state) => state.uploadResults)
  const selectedResultId = useAppStore((state) => state.selectedResultId)
  const setSelectedResultId = useAppStore((state) => state.setSelectedResultId)
  const isSSEConnected = useAppStore((state) => state.isSSEConnected)
  const mergeUploadResults = useAppStore((state) => state.mergeUploadResults)

  React.useEffect(() => {
    let isMounted = true

    async function loadCvs() {
      try {
        setIsResultsLoading(true)
        setResultsLoadError(null)
        const payload = await apiClient.get<CvsResponse>("/cvs", {
          params: {
            status: "processed",
          },
        })
        if (!isMounted || !payload.success) {
          return
        }

        const nextResults: Record<string, UploadResultType> = {}
        for (const item of payload.items) {
          const normalized = normalizeCvResult(item)
          nextResults[normalized.id] = normalized
        }

        mergeUploadResults(nextResults)
      } catch (error) {
        if (!isMounted) {
          return
        }
        setResultsLoadError(
          error instanceof Error ? error.message : "获取 CV 列表失败"
        )
      } finally {
        if (isMounted) {
          setIsResultsLoading(false)
        }
      }
    }

    loadCvs()

    return () => {
      isMounted = false
    }
  }, [mergeUploadResults])

  const results = React.useMemo(
    () =>
      Object.values(uploadResults).sort((a, b) =>
        (b.updated_at ?? b.created_at ?? "").localeCompare(
          a.updated_at ?? a.created_at ?? ""
        )
      ),
    [uploadResults]
  )

  const handleNavRoute = (item: navType) => {
    setActiveItem(item)

    if (item.url === "cv") {
      setOpen(true)
    }
    router.push(item.url)
  }

  return (
    <Sidebar
      collapsible="icon"
      className="overflow-hidden *:data-[sidebar=sidebar]:flex-row"
      {...props}
    >
      <Sidebar
        collapsible="none"
        className="w-[calc(var(--sidebar-width-icon)+1px)]! border-r"
      >
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                // size="sm"
                render={
                  <HugeiconsIcon icon={RubberDuckIcon} size={16} strokeWidth={1.5}/>
                }
              ></SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent className="px-1.5 md:px-0">
              <SidebarMenu>
                {navMain.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      tooltip={{
                        children: item.title,
                        hidden: false,
                      }}
                      onClick={() => handleNavRoute(item)}
                      isActive={activeItem?.title === item.title}
                      className="px-2.5 md:px-2"
                    >
                      <HugeiconsIcon
                        icon={item.icon}
                        size={24}
                        strokeWidth={1.5}
                      />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <UploadsDialog />
          <SettingsDialog />
        </SidebarFooter>
      </Sidebar>

      <Sidebar collapsible="none" className="hidden flex-1 md:flex">
        <SidebarHeader className="gap-3.5 border-b p-4">
          <div className="flex w-full items-center justify-between">
            <div className="text-base font-medium text-foreground">
              {activeItem?.title}
            </div>
            <Badge variant={isSSEConnected ? "secondary" : "outline"} className={getStatusClassName(isSSEConnected ? "processed" : "error")}>
              <HugeiconsIcon icon={Activity01Icon} strokeWidth={1.6} />
              {isSSEConnected ? "SSE 已连接" : "SSE 未连接"}
            </Badge>
          </div>
          <SidebarInput placeholder="按文件名搜索结果..." />
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup className="px-0">
            <SidebarGroupContent>
              {results.length ? (
                results.map((result) => (
                  <button
                    type="button"
                    key={result.id}
                    onClick={() => setSelectedResultId(result.id)}
                    className="flex w-full min-w-0 flex-col items-start gap-2 overflow-hidden border-b p-4 text-left text-sm leading-tight last:border-b-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground data-[active=true]:bg-sidebar-accent data-[active=true]:text-sidebar-accent-foreground"
                    data-active={selectedResultId === result.id}
                  >
                    <div className="flex w-full items-center gap-2">
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {result.filename}
                      </span>
                    </div>
                    <div className="flex w-full min-w-0 items-center gap-2 text-xs text-muted-foreground">
                      <span
                        className={cn(
                          "inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none ring-1",
                          getStatusClassName(result.status)
                        )}
                      >
                        {getStatusLabel(result.status)}
                      </span>
                      <span className="min-w-0 truncate">
                        {result.job_name || result.job_id}
                      </span>
                    </div>
                  </button>
                ))
              ) : isResultsLoading ? (
                <div className="p-4 text-xs text-muted-foreground">
                  CV 列表加载中...
                </div>
              ) : resultsLoadError ? (
                <div className="p-4 text-xs text-destructive">
                  {resultsLoadError}
                </div>
              ) : (
                <div className="p-4 text-xs text-muted-foreground">
                  还没有上传记录。点击左下角上传按钮开始处理 CV。
                </div>
              )}
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
      </Sidebar>
    </Sidebar>
  )
}
