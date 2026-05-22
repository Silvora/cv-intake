import { useState, useRef, useCallback } from "react"

export interface PDFFileInfo {
  id: string
  name: string
  relativePath: string
  size: number
  file: File
  objectUrl?: string
}

export interface UseFolderPDFFilesReturn {
  files: PDFFileInfo[]
  isLoading: boolean
  error: string | null
  folderInputRef: React.RefObject<HTMLInputElement | null>
  fileInputRef: React.RefObject<HTMLInputElement | null>
  openFolderPicker: () => void
  openFilePicker: () => void
  reset: () => void
  handleFolderChange: (
    event: React.ChangeEvent<HTMLInputElement>
  ) => Promise<void>
  handleFileChange: (
    event: React.ChangeEvent<HTMLInputElement>
  ) => Promise<void>
  revokeObjectURL: (fileInfo: PDFFileInfo) => void
}

export function useFolderPDFFiles(): UseFolderPDFFilesReturn {
  const folderInputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const filesRef = useRef<PDFFileInfo[]>([])
  const [files, setFiles] = useState<PDFFileInfo[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const revokeObjectURL = useCallback((fileInfo: PDFFileInfo) => {
    if (fileInfo.objectUrl) {
      URL.revokeObjectURL(fileInfo.objectUrl)
    }
  }, [])

  const toPDFInfos = useCallback((selectedFiles: FileList) => {
    const fileArray = Array.from(selectedFiles)
    const pdfFiles = fileArray.filter((file) =>
      file.name.toLowerCase().endsWith(".pdf")
    )

    if (pdfFiles.length === 0) {
      return {
        files: [],
        error: "未找到 PDF 文件",
      }
    }

    const pdfInfos: PDFFileInfo[] = pdfFiles.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${file.webkitRelativePath || file.name}`,
      name: file.name,
      relativePath: file.webkitRelativePath || file.name,
      size: file.size,
      file,
      objectUrl: URL.createObjectURL(file),
    }))

    return {
      files: pdfInfos,
      error: null,
    }
  }, [])

  const reset = useCallback(() => {
    filesRef.current.forEach((file) => revokeObjectURL(file))
    filesRef.current = []
    setFiles([])
    setError(null)
    setIsLoading(false)
    if (folderInputRef.current) {
      folderInputRef.current.value = ""
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }, [revokeObjectURL])

  const handleSelection = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>, emptyMessage: string) => {
      const selectedFiles = event.target.files
      if (!selectedFiles || selectedFiles.length === 0) {
        setError(emptyMessage)
        return
      }

      setIsLoading(true)
      setError(null)
      filesRef.current.forEach((file) => revokeObjectURL(file))
      filesRef.current = []
      setFiles([])

      try {
        const next = toPDFInfos(selectedFiles)
        if (next.error) {
          setError(next.error)
        } else {
          filesRef.current = next.files
          setFiles(next.files)
        }
      } catch (err) {
        console.error("读取文件出错:", err)
        setError("读取文件时发生错误，请重试")
      } finally {
        setIsLoading(false)
        if (folderInputRef.current) {
          folderInputRef.current.value = ""
        }
        if (fileInputRef.current) {
          fileInputRef.current.value = ""
        }
      }
    },
    [revokeObjectURL, toPDFInfos]
  )

  const handleFolderChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) =>
      handleSelection(event, "未选择任何文件夹"),
    [handleSelection]
  )

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) =>
      handleSelection(event, "未选择任何文件"),
    [handleSelection]
  )

  const openFolderPicker = useCallback(() => {
    folderInputRef.current?.click()
  }, [])

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  return {
    files,
    isLoading,
    error,
    folderInputRef,
    fileInputRef,
    openFolderPicker,
    openFilePicker,
    reset,
    handleFolderChange,
    handleFileChange,
    revokeObjectURL,
  }
}
