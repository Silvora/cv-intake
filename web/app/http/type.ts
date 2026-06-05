export type UploadStatus =
  | "idle"
  | "queued"
  | "uploading"
  | "processing"
  | "processed"
  | "deleted"
  | "ocr_no_text"
  | "skipped_duplicate_md5"
  | "skipped_empty_file"
  | "skipped_non_pdf"
  | "error"

export type ProcessingStage =
  | "queued"
  | "ocr"
  | "summary"
  | "verify"
  | "score"
  | "interview"
  | "ocr_no_text"
  | "error"

// 前端左侧列表和上传后的岗位列表都用这套最小字段。
export interface JobListType {
  id: string
  label: string
  description: string
}

// 后端 /jobs 接口返回的单条岗位数据。
export interface JobApiItem {
  id: string
  label: string
  description: string
}

export interface JobsResponse {
  success: boolean
  items: JobApiItem[]
  total: number
}

export interface JobMutationResponse {
  success: boolean
  message: string
  item: JobApiItem
}

// 前端上传对话框里选择的单个文件。
export interface UploadFileInput {
  file: File
  name: string
}

// 后端 /cvs、/cvs/{id}、/upload 都复用的简历记录结构。
export interface CvRecordApiItem {
  id: string
  filename: string
  job_id: string
  job_name?: string
  file_path?: string
  md5?: string | null
  status: UploadStatus
  processing_stage?: ProcessingStage | null
  processing_attempt?: number | null
  error?: string | null
  ocr_engine?: string | null
  resume_text?: string | null
  resume_text_length?: number | null
  job_text?: string | null
  job_text_length?: number | null
  resume_summary?: Record<string, unknown> | null
  verify_result?: Record<string, unknown> | null
  score_result?: Record<string, unknown> | null
  interview_result?: Record<string, unknown> | null
  starred?: boolean
  final_answer?: string | null
  data?: CvLegacyData | null
  created_at?: string
  updated_at?: string
}

export interface CvsResponse {
  success: boolean
  items: CvRecordApiItem[]
  total: number
}

export interface CvDetailResponse {
  success: boolean
  item: CvRecordApiItem
}

export interface CvMutationResponse {
  success: boolean
  message: string
  item: CvRecordApiItem
}

export interface UploadResponse {
  success: boolean
  message: string
  count: number
  items: CvRecordApiItem[]
}

export interface SettingsApiItem {
  model: string
  temperature: number
  api_key: string
  base_url: string
  zhipu_search_api_key: string
}

export interface SettingsResponse {
  success: boolean
  item: SettingsApiItem
}

export interface SettingsMutationResponse {
  success: boolean
  message: string
  item: SettingsApiItem
}

// SSE 推送的 results 事件 payload：key 是记录 id，value 是完整记录。
export type CvResultsSsePayload = Record<string, CvRecordApiItem>

// 后端为了兼容旧前端保留了一层 data.result，这里把结构显式声明出来。
export interface CvLegacyData {
  result?: {
    info?: {
      name?: string
      phone?: string
      email?: string
      github_url?: string
      location?: string
      summary?: string
      schools?: Array<{
        school_name?: string
        degree?: string
        study_period?: string
      }>
    }
    experience?: {
      experience_summary?: string
      work_experiences?: Array<{
        company?: string
        project_name?: string
        duration?: string
        projects?: string[] | string
      }>
    }
    skill?: {
      skills?: string[]
      bonus_items?: string[]
      certificates?: string[]
      languages?: string[]
    }
    score?: {
      score?: {
        overall?: number
        must_have_match?: number
        experience_match?: number
        skill_match?: number
        education_match?: number
      }
      reason?: {
        why_this_score?: string
        met_requirements?: string[]
        missing_requirements?: string[]
        risk_points?: string[]
      }
      improvement_suggestions?: string[]
    }
    meta?: {
      generated_at?: string
    }
    interview?: Record<string, unknown>
  }
  error?: {
    code?: string
    message?: string
    ocr_engine?: string
  }
}
