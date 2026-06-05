"use client"

import * as React from "react"

import {
  useCreateJobMutation,
  useDeleteJobMutation,
  useJobsQuery,
  useUpdateJobMutation,
} from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
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
  Card,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { Delete02Icon, PencilEdit02Icon, PlusSignIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

type JobFormState = {
  id: string | null
  label: string
  description: string
}

const emptyForm: JobFormState = {
  id: null,
  label: "",
  description: "",
}

export function JobsSettingsPanel() {
  const jobsQuery = useJobsQuery()
  const createJobMutation = useCreateJobMutation()
  const updateJobMutation = useUpdateJobMutation()
  const deleteJobMutation = useDeleteJobMutation()
  const setJobList = useAppStore((state) => state.setJobList)
  const [form, setForm] = React.useState<JobFormState>(emptyForm)
  const [error, setError] = React.useState<string | null>(null)
  const [deletingJobId, setDeletingJobId] = React.useState<string | null>(null)

  const jobs = jobsQuery.data ?? []

  React.useEffect(() => {
    if (!jobsQuery.data) {
      return
    }
    setJobList(jobsQuery.data)
  }, [jobsQuery.data, setJobList])

  const isSubmitting = createJobMutation.isPending || updateJobMutation.isPending

  const handleFieldChange = React.useCallback(
    (key: keyof JobFormState, value: string) => {
      setForm((current) => ({
        ...current,
        [key]: value,
      }))
    },
    []
  )

  const handleReset = React.useCallback(() => {
    setForm(emptyForm)
    setError(null)
  }, [])

  const handleEdit = React.useCallback((job: { id: string; label: string; description: string }) => {
    setForm({
      id: job.id,
      label: job.label,
      description: job.description,
    })
    setError(null)
  }, [])

  const handleSubmit = React.useCallback(async () => {
    const label = form.label.trim()
    const description = form.description.trim()

    if (!label) {
      setError("岗位名称不能为空")
      return
    }

    setError(null)

    try {
      if (form.id) {
        await updateJobMutation.mutateAsync({
          id: form.id,
          label,
          description,
        })
      } else {
        await createJobMutation.mutateAsync({
          label,
          description,
        })
      }
      handleReset()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败")
    }
  }, [createJobMutation, form.description, form.id, form.label, handleReset, updateJobMutation])

  const handleDelete = React.useCallback(async () => {
    if (!deletingJobId) {
      return
    }

    try {
      await deleteJobMutation.mutateAsync(deletingJobId)
      if (form.id === deletingJobId) {
        handleReset()
      }
      setDeletingJobId(null)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除失败")
      setDeletingJobId(null)
    }
  }, [deleteJobMutation, deletingJobId, form.id, handleReset])

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-5">
        <h2 className="text-sm font-medium">Jobs</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          管理上传时可选择的岗位，以及每个岗位对应的 JD 文本。
        </p>
      </div>

      <div className="grid flex-1 gap-0 overflow-hidden md:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="border-b px-6 py-5 md:border-r md:border-b-0">
          <FieldSet>
            <FieldGroup>
              <Field>
                <FieldLabel>岗位名称</FieldLabel>
                <FieldContent>
                  <Input
                    value={form.label}
                    onChange={(event) => handleFieldChange("label", event.target.value)}
                    placeholder="例如：前端工程师"
                  />
                </FieldContent>
              </Field>

              <Field>
                <FieldLabel>岗位描述</FieldLabel>
                <FieldContent>
                  <Textarea
                    value={form.description}
                    onChange={(event) =>
                      handleFieldChange("description", event.target.value)
                    }
                    className="h-78"
                    placeholder="填写 JD，用于后续简历评分。"
                  />
                  <FieldDescription>
                    保存后上传 CV 时会把该 JD 传入工作流评分节点。
                  </FieldDescription>
                </FieldContent>
              </Field>
            </FieldGroup>
          </FieldSet>

          {error ? <p className="mt-4 text-xs text-destructive">{error}</p> : null}

          <div className="mt-5 flex gap-2">
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Spinner />
                  保存中
                </>
              ) : (
                <>
                  <HugeiconsIcon
                    icon={form.id ? PencilEdit02Icon : PlusSignIcon}
                    strokeWidth={1.8}
                  />
                  {form.id ? "更新岗位" : "新增岗位"}
                </>
              )}
            </Button>
            <Button variant="outline" onClick={handleReset} disabled={isSubmitting}>
              清空
            </Button>
          </div>
        </aside>

        <section className="min-h-0 overflow-auto px-6 py-5">
          {jobsQuery.isLoading ? (
            <div className="flex min-h-60 items-center justify-center text-muted-foreground">
              <Spinner />
            </div>
          ) : jobsQuery.error ? (
            <div className="rounded-lg border border-dashed p-4 text-destructive">
              岗位列表加载失败
            </div>
          ) : jobs.length ? (
            <div className="grid gap-3">
              {jobs.map((job) => (
                <Card key={job.id} size="sm">
                  <CardHeader className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <CardTitle className="truncate" title={job.label}>
                        {job.label}
                      </CardTitle>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(job)}
                      >
                        <HugeiconsIcon icon={PencilEdit02Icon} strokeWidth={1.8} />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeletingJobId(job.id)}
                        disabled={deleteJobMutation.isPending}
                      >
                        <HugeiconsIcon icon={Delete02Icon} strokeWidth={1.8} />
                      </Button>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-4 text-muted-foreground">
              还没有岗位，先在左侧新增一条。
            </div>
          )}
        </section>
      </div>

      <AlertDialog open={Boolean(deletingJobId)} onOpenChange={(open) => !open && setDeletingJobId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除岗位</AlertDialogTitle>
            <AlertDialogDescription>
              这会删除当前岗位记录。已上传的 CV 记录不会自动删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteJobMutation.isPending}>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleteJobMutation.isPending}>
              {deleteJobMutation.isPending ? "删除中" : "确认删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
