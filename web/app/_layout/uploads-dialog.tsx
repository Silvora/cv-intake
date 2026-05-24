"use client"

import {
    File01Icon,
    FolderLibraryIcon,
    InboxUploadIcon,
    Tick02Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import * as React from "react"
import { toast } from "sonner"

import { useJobsQuery, useUploadCvsMutation } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import {
    Field,
    FieldContent,
    FieldDescription,
    FieldGroup,
    FieldLabel,
    FieldSet,
} from "@/components/ui/field"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { useFolderPDFFiles } from "@/hooks/useFolderPDFFiles"
import { cn } from "@/lib/utils"

export function UploadsDialog() {
  const [open, setOpen] = React.useState(false)
  const {
    files,
    error,
    folderInputRef,
    fileInputRef,
    openFolderPicker,
    openFilePicker,
    reset,
    handleFolderChange,
    handleFileChange,
  } = useFolderPDFFiles()
  const {
    selectedJobId,
    setSelectedJobId,
    setUploading,
    isUploading,
    setUploadError,
    uploadError,
  } = useAppStore()
  const jobsQuery = useJobsQuery()
  const uploadMutation = useUploadCvsMutation()

  const jobList = jobsQuery.data ?? []
  const selectedJob = React.useMemo(
    () => jobList.find((job) => job.id === selectedJobId),
    [jobList, selectedJobId]
  )

  React.useEffect(() => {
    if (!open) {
      return
    }
    if (!jobList.length || selectedJobId) {
      return
    }
    setSelectedJobId(jobList[0].id)
  }, [jobList, open, selectedJobId, setSelectedJobId])

  React.useEffect(() => {
    if (open) {
      return
    }

    reset()
    setUploadError(null)
  }, [open, reset, setUploadError])

  const handleDialogChange = React.useCallback(
    (nextOpen: boolean) => {
      setOpen(nextOpen)
      if (!nextOpen) {
        setUploadError(null)
      }
    },
    [setUploadError]
  )

  const handleConfirmUpload = React.useCallback(async () => {
    if (!files.length) {
      setUploadError("请先选择 PDF 文件或文件夹")
      return
    }

    if (!selectedJobId) {
      setUploadError("请选择岗位类型")
      return
    }

    try {
      setUploading(true)
      setUploadError(null)

      const payload = await uploadMutation.mutateAsync({
        files: files.map((item) => ({ file: item.file, name: item.name })),
        jobId: selectedJobId,
      })

      toast.success(`已提交 ${payload.count} 份 CV，正在处理中`)
      setOpen(false)
    } catch (uploadError) {
      const message =
        uploadError instanceof Error ? uploadError.message : "上传失败"
      setUploadError(message)
      toast.error(message)
    } finally {
      setUploading(false)
    }
  }, [
    files,
    selectedJobId,
    setUploadError,
    setUploading,
    uploadMutation,
  ])

  return (
    <Dialog open={open} onOpenChange={handleDialogChange}>
      <DialogTrigger
        render={
          <Button variant="ghost">
            <HugeiconsIcon icon={InboxUploadIcon} size={24} strokeWidth={1.5} />
          </Button>
        }
      />
      <DialogContent
        showCloseButton={false}
        className="overflow-hidden p-0 md:max-h-160 md:max-w-190"
      >
        <input
          ref={folderInputRef}
          type="file"
          // @ts-expect-error non-standard but supported by Chromium
          webkitdirectory=""
          multiple
          onChange={handleFolderChange}
          className="hidden"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="grid gap-0 md:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="border-b bg-muted/20 p-5 md:border-r md:border-b-0">
            <DialogHeader className="gap-2">
              <DialogTitle>上传 CV</DialogTitle>
              <DialogDescription>
                选择单个文件、多个 PDF，或整个文件夹；再指定岗位类型后提交处理。
              </DialogDescription>
            </DialogHeader>

            <div className="mt-6 grid gap-3">
              <Button
                variant="outline"
                className="justify-start"
                onClick={openFilePicker}
                disabled={isUploading}
              >
                <HugeiconsIcon icon={File01Icon} strokeWidth={1.8} />
                选择文件
              </Button>
              <Button
                variant="outline"
                className="justify-start"
                onClick={openFolderPicker}
                disabled={isUploading}
              >
                <HugeiconsIcon icon={FolderLibraryIcon} strokeWidth={1.8} />
                选择文件夹
              </Button>
            </div>

            <FieldSet className="mt-6">
              <FieldGroup>
                <Field>
                  <FieldLabel>岗位类型</FieldLabel>
                  <FieldContent>
                    <Select
                      value={selectedJobId}
                      onValueChange={(value) => setSelectedJobId(String(value))}
                    >
                      <SelectTrigger className="h-auto min-h-9 w-full px-3 py-2 text-sm">
                        <SelectValue>
                          {selectedJob?.label || "选择岗位"}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {jobList.map((job) => (
                          <SelectItem
                            key={job.id}
                            value={job.id}
                            className="items-start py-2"
                          >
                            <span className="font-medium">{job.label}</span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FieldDescription
                      className={cn(
                        "max-h-57.5 overflow-y-auto rounded-md border bg-muted/30 px-3 py-2"
                      )}
                    >
                      {jobsQuery.isLoading
                        ? "岗位列表加载中..."
                        : jobsQuery.error
                          ? "获取岗位列表失败"
                          : selectedJob?.description || "选择后将使用对应 JD 处理所有文件。"}
                    </FieldDescription>
                  </FieldContent>
                </Field>
              </FieldGroup>
            </FieldSet>
          </aside>

          <section className="flex min-h-130 flex-col">
            <div className="border-b px-5 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">待上传文件</div>
                  <div className="text-muted-foreground">
                    {files.length
                      ? `已选 ${files.length} 份 PDF`
                      : "尚未选择任何 PDF"}
                  </div>
                </div>
                {files.length ? (
                  <Badge variant="outline">{files.length} files</Badge>
                ) : null}
              </div>
              {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
              {uploadError ? (
                <p className="mt-2 text-xs text-destructive">{uploadError}</p>
              ) : null}
            </div>

            <ScrollArea className="flex-1">
              <div className="grid gap-3 p-5">
                {files.length ? (
                  files.map((file) => (
                    <div
                      key={file.id}
                      className="rounded-lg border bg-card px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{file.name}</div>
                          <div className="truncate text-muted-foreground">
                            {file.relativePath}
                          </div>
                        </div>
                        <Badge variant="secondary">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex h-full min-h-70 items-center justify-center rounded-lg border border-dashed text-muted-foreground">
                    选择文件或文件夹后，这里会列出待处理的 PDF
                  </div>
                )}
              </div>
            </ScrollArea>

            <DialogFooter className="border-t px-5 py-4">
              <Button
                variant="outline"
                onClick={() => {
                  reset()
                  setUploadError(null)
                }}
                disabled={isUploading}
              >
                清空
              </Button>
              <Button onClick={handleConfirmUpload} disabled={isUploading}>
                {isUploading ? (
                  <>
                    <Spinner />
                    提交中
                  </>
                ) : (
                  <>
                    <HugeiconsIcon icon={Tick02Icon} strokeWidth={1.8} />
                    确认并处理
                  </>
                )}
              </Button>
            </DialogFooter>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
