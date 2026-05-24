import type { CvRecordApiItem } from "@/app/http/type"

export function getStatusLabel(status: CvRecordApiItem["status"]) {
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

export function getStatusClassName(status: CvRecordApiItem["status"]) {
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

export function getStatusTone(status: CvRecordApiItem["status"]) {
  switch (status) {
    case "processed":
      return "secondary"
    case "processing":
    case "uploading":
      return "default"
    case "error":
    case "skipped_empty_file":
    case "skipped_non_pdf":
      return "destructive"
    default:
      return "outline"
  }
}

export function getOverallScore(
  result: Pick<CvRecordApiItem, "score_result" | "data">
) {
  const scoreResult = result.score_result as
    | { score?: { overall?: number | null } }
    | null
    | undefined

  const directScore = scoreResult?.score?.overall
  if (typeof directScore === "number" && Number.isFinite(directScore)) {
    return directScore
  }

  const legacyScore = result.data?.result?.score?.score?.overall
  if (typeof legacyScore === "number" && Number.isFinite(legacyScore)) {
    return legacyScore
  }

  return null
}

export function getScoreLabel(score?: number | null) {
  if (typeof score !== "number") return "未评分"
  return `${score}分`
}

export function getScoreTone(score?: number | null) {
  if (typeof score !== "number") return "bg-muted text-muted-foreground"
  if (score <= 30) return "bg-rose-500/15 text-rose-700 ring-rose-500/20"
  if (score <= 60) return "bg-amber-500/15 text-amber-700 ring-amber-500/20"
  if (score <= 90) return "bg-sky-500/15 text-sky-700 ring-sky-500/20"
  return "bg-emerald-500/15 text-emerald-700 ring-emerald-500/20"
}

export function getScoreBandTone(score?: number | null) {
  if (typeof score !== "number") return "bg-muted/20 text-muted-foreground ring-border"
  if (score <= 30) return "bg-rose-500/12 text-rose-700 ring-rose-500/20"
  if (score <= 60) return "bg-amber-500/12 text-amber-700 ring-amber-500/20"
  if (score <= 90) return "bg-sky-500/12 text-sky-700 ring-sky-500/20"
  return "bg-emerald-500/12 text-emerald-700 ring-emerald-500/20"
}

export function getScoreItemTone(score?: number | null) {
  if (typeof score !== "number") return "bg-muted/20 text-muted-foreground ring-border"
  if (score <= 30) return "bg-rose-500/10 text-rose-700 ring-rose-500/20"
  if (score <= 60) return "bg-amber-500/10 text-amber-700 ring-amber-500/20"
  if (score <= 90) return "bg-sky-500/10 text-sky-700 ring-sky-500/20"
  return "bg-emerald-500/10 text-emerald-700 ring-emerald-500/20"
}

export function getScoreBand(score?: number | null) {
  if (typeof score !== "number") return "暂无"
  if (score <= 30) return "0-30"
  if (score <= 60) return "31-60"
  if (score <= 90) return "61-90"
  return "91-100"
}
