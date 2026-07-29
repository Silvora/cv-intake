"use client"

import { usePathname } from "next/navigation"

import { useCvDetailQuery } from "@/app/http/useApi"
import { AppSidebar } from "./components/app-sidebar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"

export default function Page({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const cvId = pathname.startsWith("/cv/") ? pathname.split("/")[2] : undefined
  const cvQuery = useCvDetailQuery(cvId)
  const selectedCv = cvQuery.data ?? null

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="sticky top-0 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
          <div className="flex min-w-0 items-center gap-2">
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
          </div>
        </header>
        <div className="w-full flex-1">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  )
}
