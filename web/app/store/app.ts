import { create } from "zustand"

import type { CvRecordApiItem, JobListType } from "@/app/http/type"
import type { PDFFileInfo } from "@/hooks/useFolderPDFFiles"

export interface UserConfigType {
  name: string
  apiBaseUrl: string
}

export type UploadResultType = CvRecordApiItem

interface AppStateType {
  userConfig: UserConfigType
  jobList: JobListType[]
  selectedJobId: string
  selectedFiles: PDFFileInfo[]
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
      clearUploads: () =>
        set({
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
