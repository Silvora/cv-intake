"use client"

import * as React from "react"
import { BriefcaseBusiness, Check, ChevronsUpDown } from "lucide-react"

import type { JobListType } from "@/app/http/type"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function VersionSwitcher({
  jobs,
  value,
  onValueChange,
  isLoading,
  isError,
}: {
  jobs: JobListType[]
  value: string
  onValueChange: (value: string) => void
  isLoading?: boolean
  isError?: boolean
}) {
  const selectedJob = jobs.find((job) => job.id === value)
  const selectedLabel =
    value === "all" ? "全部岗位" : selectedJob?.label || "选择岗位"

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <SidebarMenuButton
                size="lg"
                className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <BriefcaseBusiness className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-medium">岗位类型</span>
                  <span className="">
                    {isLoading
                      ? "加载中..."
                      : isError
                        ? "加载失败"
                        : selectedLabel}
                  </span>
                </div>
                <ChevronsUpDown className="ml-auto" />
              </SidebarMenuButton>
            }
          ></DropdownMenuTrigger>
          <DropdownMenuContent
            className="max-w-full"
            align="start"
          >
            <DropdownMenuItem onSelect={() => onValueChange("all")}>
              全部岗位
              {value === "all" && <Check className="ml-auto" />}
            </DropdownMenuItem>
            {jobs.map((job) => (
              <DropdownMenuItem
                key={job.id}
                onSelect={() => onValueChange(job.id)}
              >
                <span className="min-w-0 truncate">{job.label}</span>
                {job.id === value && <Check className="ml-auto" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
