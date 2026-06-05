"use client"

import * as React from "react"

import { useSettingsQuery, useUpdateSettingsMutation } from "@/app/http/useApi"
import { useAppStore } from "@/app/store/app"
import { Button } from "@/components/ui/button"
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

type FormState = {
  model: string
  temperature: string
  api_key: string
  base_url: string
  zhipu_search_api_key: string
}

const emptyForm: FormState = {
  model: "",
  temperature: "0.7",
  api_key: "",
  base_url: "",
  zhipu_search_api_key: "",
}

export function ModelSettingsPanel() {
  const settingsQuery = useSettingsQuery()
  const updateMutation = useUpdateSettingsMutation()
  const setSettings = useAppStore((state) => state.setSettings)
  const [form, setForm] = React.useState<FormState>(emptyForm)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!settingsQuery.data) {
      return
    }

    setForm({
      model: settingsQuery.data.model,
      temperature: String(settingsQuery.data.temperature),
      api_key: settingsQuery.data.api_key,
      base_url: settingsQuery.data.base_url,
      zhipu_search_api_key: settingsQuery.data.zhipu_search_api_key,
    })
    setSettings(settingsQuery.data)
  }, [setSettings, settingsQuery.data])

  const handleChange = React.useCallback(
    (key: keyof FormState, value: string) => {
      setForm((current) => ({
        ...current,
        [key]: value,
      }))
    },
    []
  )

  const handleSubmit = React.useCallback(async () => {
    const temperature = Number(form.temperature)
    if (Number.isNaN(temperature) || temperature < 0 || temperature > 2) {
      setError("temperature 必须在 0 到 2 之间")
      return
    }

    if (
      !form.model.trim() ||
      !form.api_key.trim() ||
      !form.base_url.trim() ||
      !form.zhipu_search_api_key.trim()
    ) {
      setError("请完整填写模型与搜索配置")
      return
    }

    setError(null)

    try {
      const item = await updateMutation.mutateAsync({
        model: form.model.trim(),
        temperature,
        api_key: form.api_key.trim(),
        base_url: form.base_url.trim(),
        zhipu_search_api_key: form.zhipu_search_api_key.trim(),
      })
      setSettings(item)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败")
    }
  }, [form, setSettings, updateMutation])

  if (settingsQuery.isLoading) {
    return (
      <div className="flex min-h-80 items-center justify-center text-muted-foreground">
        <Spinner />
      </div>
    )
  }

  if (settingsQuery.error || !settingsQuery.data) {
    return (
      <div className="rounded-lg border border-dashed p-4 text-destructive">
        设置加载失败
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b px-6 py-4">
        <h2 className="text-sm font-medium">模型设置</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          配置简历抽取、核验和评分共用的 LLM 参数。
        </p>
      </div>

      <div className="min-h-0 h-[60vh] overflow-y-auto px-6 py-4">
        <FieldSet>
          <FieldGroup>
            <Field>
              <FieldLabel>Model</FieldLabel>
              <FieldContent>
                <Input
                  value={form.model}
                  onChange={(event) => handleChange("model", event.target.value)}
                  placeholder="deepseek-v4-flash"
                />
                <FieldDescription>用于 Summary、Verify、Score 三个节点。</FieldDescription>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>Temperature</FieldLabel>
              <FieldContent>
                <Input
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={form.temperature}
                  onChange={(event) => handleChange("temperature", event.target.value)}
                  placeholder="0.7"
                />
                <FieldDescription>建议保持在 0 到 1 之间。</FieldDescription>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>API Key</FieldLabel>
              <FieldContent>
                <Input
                  type="password"
                  value={form.api_key}
                  onChange={(event) => handleChange("api_key", event.target.value)}
                  placeholder="sk-..."
                />
                <FieldDescription>保存到本地 SQLite 的 `settings` 表。</FieldDescription>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>Base URL</FieldLabel>
              <FieldContent>
                <Input
                  value={form.base_url}
                  onChange={(event) => handleChange("base_url", event.target.value)}
                  placeholder="https://api.deepseek.com"
                />
                <FieldDescription>用于 OpenAI 兼容模型服务地址。</FieldDescription>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>Zhipu Search API Key</FieldLabel>
              <FieldContent>
                <Input
                  type="password"
                  value={form.zhipu_search_api_key}
                  onChange={(event) =>
                    handleChange("zhipu_search_api_key", event.target.value)
                  }
                  placeholder="zhipu-search-key"
                />
                <FieldDescription>用于 Verify 节点的联网搜索核验。</FieldDescription>
              </FieldContent>
            </Field>
          </FieldGroup>
        </FieldSet>

        {error ? <p className="mt-4 text-xs text-destructive">{error}</p> : null}
      </div>

      <div className="shrink-0 border-t bg-background px-6 py-4 flex-1">
        <div className="flex justify-end">
        <Button onClick={handleSubmit} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? (
            <>
              <Spinner />
              保存中
            </>
          ) : (
            "保存模型设置"
          )}
        </Button>
        </div>
      </div>
    </div>
  )
}
