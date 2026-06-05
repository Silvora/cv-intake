"use client"

import { useCvDetailQuery, useDeleteCvMutation, useUpdateCvMutation } from "@/app/http/useApi"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
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
import { Bookmark01Icon, Delete02Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { usePathname, useRouter } from "next/navigation"
import * as React from "react"
import { AppSidebar } from "./app-sidebar"

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const cvId = pathname.startsWith("/cv/") ? pathname.split("/")[2] : undefined
  const cvQuery = useCvDetailQuery(cvId)
  const updateCvMutation = useUpdateCvMutation()
  const deleteCvMutation = useDeleteCvMutation()
  const [deleteOpen, setDeleteOpen] = React.useState(false)

  const selectedCv = cvQuery.data ?? null
  const selectedCvId = selectedCv?.id
  const selectedCvStarred = selectedCv?.starred ?? false

  const handleToggleStar = React.useCallback(async () => {
    if (!selectedCvId) {
      return
    }
    await updateCvMutation.mutateAsync({
      id: selectedCvId,
      starred: !selectedCvStarred,
    })
  }, [selectedCvId, selectedCvStarred, updateCvMutation])

  const handleDelete = React.useCallback(async () => {
    if (!selectedCvId) {
      return
    }
    await deleteCvMutation.mutateAsync(selectedCvId)
    setDeleteOpen(false)
    router.push("/cv")
  }, [deleteCvMutation, router, selectedCvId])

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
        <header className="flex shrink-0 items-center justify-between gap-4 border-b bg-background p-4">
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

          {selectedCv?.filename ? (
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant={selectedCv.starred ? "secondary" : "outline"}
                onClick={handleToggleStar}
                disabled={updateCvMutation.isPending}
                className={selectedCv.starred?"bg-yellow-200 text-yellow-800":""}
              >
                <HugeiconsIcon size={14} icon={Bookmark01Icon} strokeWidth={1.8} />
                {selectedCv.starred ? "已标记" : "标记"}
              </Button>
              <Button
                variant="destructive"
                onClick={() => setDeleteOpen(true)}
                disabled={deleteCvMutation.isPending}
              >
                <HugeiconsIcon icon={Delete02Icon} strokeWidth={1.8} />
                删除
              </Button>
            </div>
          ) : null}
        </header>
        <div className="w-full flex-1 p-4">{children}</div>

        <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>删除当前简历</AlertDialogTitle>
              <AlertDialogDescription>
                删除后会移除当前 CV 记录和关联 PDF，操作不可恢复。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteCvMutation.isPending}>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={deleteCvMutation.isPending}
              >
                {deleteCvMutation.isPending ? "删除中" : "确认删除"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SidebarInset>
    </SidebarProvider>
  )
}
