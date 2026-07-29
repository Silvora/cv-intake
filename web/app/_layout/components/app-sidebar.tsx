"use client"

import * as React from "react"
import { usePathname } from "next/navigation"

import { useCvsQuery, useJobsQuery } from "@/app/http/useApi"
import { SearchForm } from "./search-form"
import { SettingsDialog } from "./settings-dialog"
import { UploadsDialog } from "./uploads-dialog"
import { VersionSwitcher } from "./version-switcher"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

const ALL_JOBS_VALUE = "all"

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()
  const jobsQuery = useJobsQuery()
  const [selectedJobId, setSelectedJobId] = React.useState(ALL_JOBS_VALUE)
  const [keyword, setKeyword] = React.useState("")
  const deferredKeyword = React.useDeferredValue(keyword)
  const cvsQuery = useCvsQuery({
    jobId: selectedJobId === ALL_JOBS_VALUE ? undefined : selectedJobId,
    keyword: deferredKeyword,
  })

  const jobs = jobsQuery.data ?? []
  const cvs = cvsQuery.data ?? []

  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <VersionSwitcher
          jobs={jobs}
          value={selectedJobId}
          onValueChange={setSelectedJobId}
          isLoading={jobsQuery.isLoading}
          isError={Boolean(jobsQuery.error)}
        />
        <SearchForm value={keyword} onValueChange={setKeyword} />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {cvs.length ? (
                cvs.map((cv) => {
                  const url = `/cv/${cv.id}`

                  return (
                    <SidebarMenuItem key={cv.id}>
                      <SidebarMenuButton
                        render={<a href={url}>{cv.filename}</a>}
                        isActive={pathname === url}
                      ></SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })
              ) : (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>
                    {cvsQuery.error
                      ? "获取简历列表失败"
                      : keyword || selectedJobId !== ALL_JOBS_VALUE
                        ? "没有匹配的简历"
                        : "暂无简历"}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="grid grid-cols-2 gap-2 border-t [&_button]:h-9 [&_button]:w-full [&_button]:cursor-pointer [&_button]:rounded-md [&_button]:transition-colors [&_button:hover]:bg-sidebar-accent [&_button:hover]:text-sidebar-accent-foreground">
        <div className="flex items-center justify-center">
          <UploadsDialog />
        </div>
        <div className="flex items-center justify-center">
          <SettingsDialog />
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
