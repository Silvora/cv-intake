"use client"

import { useRouter } from "next/navigation"
import * as React from "react"

import { useCvsQuery } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
import {
    getOverallScore,
    getScoreLabel,
    getScoreTone,
    getStatusClassName,
    getStatusLabel,
} from "@/app/utils/status"
import { Badge } from "@/components/ui/badge"
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
import { useCVUploadSSE } from "@/hooks/useCVUploadSSE"
import { cn } from "@/lib/utils"
import { Activity01Icon, PdfIcon, RubberDuckIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { usePathname } from "next/navigation"
import { SettingsDialog } from "./settings-dialog"
import { UploadsDialog } from "./uploads-dialog"

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

interface NavType {
  title: string
  url: string
  icon: IconSvgObject
  isActive: boolean
}

const navMain: NavType[] = [
  {
    title: "CV",
    url: "/cv",
    icon: PdfIcon,
    isActive: true,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const apiBaseUrl = useAppStore((state) => state.userConfig.apiBaseUrl)
  useCVUploadSSE(apiBaseUrl)

  const { setOpen } = useSidebar()
  const router = useRouter()
  const cvsQuery = useCvsQuery()
  const pathname = usePathname()
  const activeItem = React.useMemo(
    () => navMain.find((item) => pathname.startsWith(item.url)) ?? navMain[0],
    [pathname]
  )

  const handleNavRoute = React.useCallback(
    (item: NavType) => {
      if (item.url === "/cv") {
        setOpen(true)
      }
      router.push(item.url)
    },
    [router, setOpen]
  )

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
                render={<HugeiconsIcon icon={RubberDuckIcon} size={16} strokeWidth={1.5} />}
              />
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent className="min-w-0 px-1.5 md:px-0">
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
                      <HugeiconsIcon icon={item.icon} size={24} strokeWidth={1.5} />
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

      <Sidebar collapsible="none" className="hidden flex-1 md:flex overflow-hidden">
        <SidebarHeader className="gap-3.5 border-b p-4">
          <div className="flex w-full items-center justify-between">
            <div className="text-base font-medium text-foreground">
              {activeItem?.title}
            </div>
            <Badge
              variant={cvsQuery.isFetching ? "outline" : "secondary"}
              className={cn(
                getStatusClassName(cvsQuery.isFetching ? "processing" : "processed")
              )}
            >
              <HugeiconsIcon icon={Activity01Icon} strokeWidth={1.6} />
              {cvsQuery.isFetching ? "列表更新中" : "列表已加载"}
            </Badge>
          </div>
          <SidebarInput placeholder="按文件名搜索结果..." />
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup className="px-0">
            <SidebarGroupContent>
              {cvsQuery.data?.length ? (
                cvsQuery.data.map((result) => (
                  <button
                    type="button"
                    key={result.id}
                    onClick={() => router.push(`/cv/${result.id}`)}
                    className="flex-1 flex w-full min-w-0 flex-col items-stretch gap-2 overflow-hidden border-b p-4 text-left text-sm leading-tight last:border-b-0 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  >
                    <div className="w-full min-w-0 truncate">
                      <span className="block w-full max-w-full truncate font-medium">
                        {result.filename}
                      </span>
                    </div>
                    <div className="flex w-full min-w-0 items-center gap-2 text-xs text-muted-foreground">
                      <span
                        className={`inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none ring-1 ${getScoreTone(
                          getOverallScore(result)
                        )}`}
                      >
                        {getScoreLabel(getOverallScore(result))}
                      </span>
                      <span
                        className={`inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none ring-1 ${getStatusClassName(
                          result.status
                        )}`}
                      >
                        {getStatusLabel(result.status)}
                      </span>
                      <span className="min-w-0 flex-1 truncate">
                        {result.job_name || result.job_id}
                      </span>
                    </div>
                  </button>
                ))
              ) : cvsQuery.isLoading ? (
                <div className="p-4 text-xs text-muted-foreground">
                  CV 列表加载中...
                </div>
              ) : cvsQuery.error ? (
                <div className="p-4 text-xs text-destructive">
                  获取简历列表失败
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
