"use client"

import * as React from "react"

import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { QueryClientProvider, createReactQueryClient } from "@/api"

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => createReactQueryClient())

  return (
    <ThemeProvider defaultTheme="light">
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  )
}
