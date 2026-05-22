"use client"

import { AppSidebar } from "./app-sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { useAppStore } from "@/app/store/app"

export default function Layout({ children }: { children: React.ReactNode }) {
  const uploadResults = useAppStore((state) => state.uploadResults)
  const selectedResultId = useAppStore((state) => state.selectedResultId)

  const selectedCv =
    (selectedResultId ? uploadResults[selectedResultId] : null) ?? null

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "320px",
        } as React.CSSProperties
      }
    >
      <AppSidebar />
      <SidebarInset className="flex h-dvh w-full flex-col overflow-hidden">
        <header className="flex shrink-0 items-center gap-2 border-b bg-background p-4">
          <SidebarTrigger className="-ml-1" />
          <div>
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
          </div>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage>
                  {selectedCv?.filename || "未选择简历"}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>
        <div className="w-full flex-1 p-4">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  )
}
