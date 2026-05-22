import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"

import type { PDFFileInfo } from "@/hooks/useFolderPDFFiles"

export interface UserConfigType {
  name: string
  apiBaseUrl: string
}

export interface JobListType {
  id: string
  label: string
  description: string
}

export type UploadStatus =
  | "idle"
  | "queued"
  | "uploading"
  | "processing"
  | "processed"
  | "ocr_no_text"
  | "skipped_duplicate_md5"
  | "skipped_empty_file"
  | "skipped_non_pdf"
  | "error"

export interface UploadResultType {
  id: string
  filename: string
  job_id: string
  job_name?: string
  file_path?: string
  md5?: string | null
  status: UploadStatus
  created_at?: string
  updated_at?: string
  ocr_engine?: string
  resume_text?: string
  resume_text_length?: number
  jd_text_length?: number
  error?: string
  data?: {
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
    }
    error?: {
      code?: string
      message?: string
      ocr_engine?: string
    }
  }
}

interface UploadPayloadItem {
  id: string
  filename: string
  job_id: string
  job_name?: string
  md5?: string | null
  status: UploadStatus
  created_at?: string
}

interface AppStateType {
  userConfig: UserConfigType
  jobList: JobListType[]
  selectedJobId: string
  selectedFiles: PDFFileInfo[]
  uploadResults: Record<string, UploadResultType>
  selectedResultId: string | null
  isUploading: boolean
  isSSEConnected: boolean
  uploadError: string | null
  setUserConfig: (patch: Partial<UserConfigType>) => void
  setJobList: (jobList: JobListType[]) => void
  setSelectedJobId: (jobId: string) => void
  setSelectedFiles: (files: PDFFileInfo[]) => void
  clearSelectedFiles: () => void
  setUploading: (uploading: boolean) => void
  setUploadError: (error: string | null) => void
  setSSEConnected: (connected: boolean) => void
  mergeUploadResult: (result: UploadResultType) => void
  mergeUploadResults: (results: Record<string, UploadResultType>) => void
  seedAcceptedUploads: (items: UploadPayloadItem[]) => void
  setSelectedResultId: (id: string | null) => void
  clearUploads: () => void
}

const defaultJobList: JobListType[] = []

export const useAppStore = create<AppStateType>()(
  // persist(
    (set, get) => ({
      userConfig: {
        name: "",
        apiBaseUrl: "http://127.0.0.1:9000",
      },
      jobList: defaultJobList,
      selectedJobId: defaultJobList[0]?.id ?? "",
      selectedFiles: [],
      uploadResults: {},
      selectedResultId: null,
      isUploading: false,
      isSSEConnected: false,
      uploadError: null,
      setUserConfig: (patch) =>
        set((state) => ({
          userConfig: {
            ...state.userConfig,
            ...patch,
          },
        })),
      setJobList: (jobList) => set({ jobList }),
      setSelectedJobId: (jobId) => set({ selectedJobId: jobId }),
      setSelectedFiles: (files) => set({ selectedFiles: files }),
      clearSelectedFiles: () => set({ selectedFiles: [] }),
      setUploading: (isUploading) => set({ isUploading }),
      setUploadError: (uploadError) => set({ uploadError }),
      setSSEConnected: (isSSEConnected) => set({ isSSEConnected }),
      mergeUploadResult: (result) =>
        set((state) => {
          const resultId = result.md5 || result.id
          const uploadResults = {
            ...state.uploadResults,
            [resultId]: {
              ...state.uploadResults[resultId],
              ...result,
              id: resultId,
            },
          }

          return {
            uploadResults,
            selectedResultId:
              state.selectedResultId ?? resultId ?? null,
          }
        }),
      mergeUploadResults: (results) =>
        set((state) => {
          const nextResults = { ...state.uploadResults }
          for (const [id, item] of Object.entries(results)) {
            const resultId = item.md5 || item.id || id
            nextResults[resultId] = {
              ...nextResults[resultId],
              ...item,
              id: resultId,
            }
          }

          const sortedIds = Object.values(nextResults)
            .sort((a, b) =>
              (b.updated_at ?? b.created_at ?? "").localeCompare(
                a.updated_at ?? a.created_at ?? ""
              )
            )
            .map((item) => item.id)

          const selectedResultId =
            state.selectedResultId && nextResults[state.selectedResultId]
              ? state.selectedResultId
              : sortedIds[0] ?? null

          return {
            uploadResults: nextResults,
            selectedResultId,
          }
        }),
      seedAcceptedUploads: (items) =>
        set((state) => {
          const uploadResults = { ...state.uploadResults }
          for (const item of items) {
            const resultId = item.md5 || item.id
            uploadResults[resultId] = {
              ...uploadResults[resultId],
              ...item,
              id: resultId,
            }
          }

          return {
            uploadResults,
            selectedResultId:
              items[0]?.md5 ?? items[0]?.id ?? state.selectedResultId,
          }
        }),
      setSelectedResultId: (selectedResultId) => set({ selectedResultId }),
      clearUploads: () =>
        set({
          uploadResults: {},
          selectedResultId: null,
          uploadError: null,
          isUploading: false,
        }),
    }),
  //   {
  //     name: "app-chat-storage",
  //     storage: createJSONStorage(() => localStorage),
  //     partialize: (state) => ({
  //       userConfig: state.userConfig,
  //       jobList: state.jobList,
  //       selectedJobId: state.selectedJobId,
  //     }),
  //     version: 2,
  //   }
  // )
)
