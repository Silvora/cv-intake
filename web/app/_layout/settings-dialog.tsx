"use client"

import {
  Briefcase01Icon,
  Settings,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { JobsSettingsPanel } from "./components/jobs-settings-panel"
import { ModelSettingsPanel } from "./components/model-settings-panel"

type SettingsTab = "model" | "jobs"

const navItems: Array<{
  key: SettingsTab
  name: string
  description: string
  icon: typeof Settings
}> = [
  {
    key: "model",
    name: "模型",
    description: "",
    icon: Settings,
  },
  {
    key: "jobs",
    name: "Jobs",
    description: "",
    icon: Briefcase01Icon,
  },
]

export function SettingsDialog() {
  const [open, setOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<SettingsTab>("model")

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="ghost">
            <HugeiconsIcon icon={Settings} size={24} strokeWidth={1.5} />
          </Button>
        }
      />
      <DialogContent
        showCloseButton={false}
        className="overflow-hidden p-0 h-[75vh] md:max-w-240"
      >
        <SidebarProvider className="h-full items-start">
          <Sidebar collapsible="none" className="hidden h-full w-72! border-r md:flex">
            <SidebarContent>
              <SidebarGroup className="px-3 py-4">
                <div className="px-2 pb-4">
                  <div className="text-sm font-medium">设置</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    当前支持模型配置和岗位管理。
                  </div>
                </div>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {navItems.map((item) => (
                      <SidebarMenuItem key={item.key}>
                        <SidebarMenuButton
                          isActive={activeTab === item.key}
                          onClick={() => setActiveTab(item.key)}
                          className="h-auto items-start px-3 py-3"
                        >
                          <HugeiconsIcon icon={item.icon} size={18} strokeWidth={1.8} />
                          <div className="min-w-0">
                            <div className="font-medium">{item.name}</div>
                            <div className="mt-1 text-[11px] text-muted-foreground">
                              {item.description}
                            </div>
                          </div>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>
          </Sidebar>

          <main className="flex h-full min-h-0 h-full flex-1 flex-col overflow-hidden">
            <div className="shrink-0 flex gap-2 border-b px-4 py-3 md:hidden">
              {navItems.map((item) => (
                <Button
                  key={item.key}
                  variant={activeTab === item.key ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab(item.key)}
                >
                  <HugeiconsIcon icon={item.icon} size={16} strokeWidth={1.8} />
                  {item.name}
                </Button>
              ))}
            </div>
            {activeTab === "model" ? <ModelSettingsPanel /> : null}
            {activeTab === "jobs" ? <JobsSettingsPanel /> : null}
          </main>
        </SidebarProvider>
      </DialogContent>
    </Dialog>
  )
}
