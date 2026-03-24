import React, { FC, useEffect, useRef, useState } from 'react'
import {
  Clock3,
  FileText,
  History as HistoryIcon,
  PanelLeftClose,
  PanelLeftOpen,
  PencilLine,
  SlidersHorizontal,
} from 'lucide-react'
import type { ImperativePanelHandle } from 'react-resizable-panels'
import { Link } from 'react-router-dom'

import logo from '@/assets/icon.svg'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { ScrollArea } from '@/components/ui/scroll-area.tsx'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip.tsx'
import {
  getDefaultMobileHomeTab,
  getHomeLayoutMode,
  getSyncedMobileHomeTab,
  type MobileHomeTab,
} from '@/lib/homeLayout.ts'
import { cn } from '@/lib/utils.ts'
import { useTaskStore } from '@/store/taskStore'

interface IProps {
  NoteForm: React.ReactNode
  Preview: React.ReactNode
  History: React.ReactNode
}

const mobileTabs: Array<{
  value: MobileHomeTab
  label: string
  description: string
  icon: typeof PencilLine
}> = [
  {
    value: 'create',
    label: '新建',
    description: '输入链接并发起生成',
    icon: PencilLine,
  },
  {
    value: 'tasks',
    label: '任务',
    description: '查看历史与切换任务',
    icon: Clock3,
  },
  {
    value: 'preview',
    label: '预览',
    description: '阅读 Markdown 与导图',
    icon: FileText,
  },
]

const getInitialLayoutMode = () => {
  if (typeof window === 'undefined') {
    return 'desktop' as const
  }

  return getHomeLayoutMode(window.innerWidth)
}

const HomeLayout: FC<IProps> = ({ NoteForm, Preview, History }) => {
  const currentTaskId = useTaskStore(state => state.currentTaskId)
  const [layoutMode, setLayoutMode] = useState(getInitialLayoutMode)
  const [mobileTab, setMobileTab] = useState<MobileHomeTab>(() =>
    getDefaultMobileHomeTab(currentTaskId)
  )
  const previousTaskIdRef = useRef<string | null>(currentTaskId)
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false)
  const [isMiddleCollapsed, setIsMiddleCollapsed] = useState(false)
  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const middlePanelRef = useRef<ImperativePanelHandle>(null)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    const syncLayoutMode = () => {
      setLayoutMode(getHomeLayoutMode(window.innerWidth))
    }

    syncLayoutMode()
    window.addEventListener('resize', syncLayoutMode)

    return () => window.removeEventListener('resize', syncLayoutMode)
  }, [])

  useEffect(() => {
    setMobileTab(current =>
      getSyncedMobileHomeTab(current, previousTaskIdRef.current, currentTaskId)
    )
    previousTaskIdRef.current = currentTaskId
  }, [currentTaskId])

  useEffect(() => {
    if (layoutMode === 'mobile') {
      setMobileTab(getDefaultMobileHomeTab(currentTaskId))
    }
  }, [currentTaskId, layoutMode])

  if (layoutMode === 'mobile') {
    const activeTab = mobileTabs.find(tab => tab.value === mobileTab) ?? mobileTabs[0]

    return (
      <div className="flex min-h-screen h-dvh flex-col overflow-hidden bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_45%,#f8fafc_100%)]">
        <header className="border-b border-white/70 bg-white/90 px-4 pb-3 pt-4 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-neutral-100 shadow-sm">
                <img src={logo} alt="logo" className="h-full w-full object-contain" />
              </div>
              <div className="min-w-0">
                <div className="text-[11px] font-semibold tracking-[0.24em] text-neutral-400 uppercase">
                  Mobile Workspace
                </div>
                <div className="truncate text-xl font-semibold text-neutral-900">BiliNote</div>
              </div>
            </div>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link
                    to="/settings"
                    className="flex h-10 w-10 items-center justify-center rounded-2xl border border-neutral-200 bg-white text-neutral-500 shadow-sm transition-colors hover:text-neutral-900"
                  >
                    <SlidersHorizontal className="h-4 w-4" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent>
                  <span>全局配置</span>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div className="mt-4 rounded-3xl border border-white/80 bg-white/75 px-4 py-3 shadow-sm">
            <div className="text-sm font-medium text-neutral-900">{activeTab.label}</div>
            <p className="mt-1 text-xs leading-5 text-neutral-500">{activeTab.description}</p>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-hidden px-3 py-3">
          <div className="h-full overflow-hidden rounded-[28px] border border-white/70 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
            {mobileTab === 'create' ? (
              <div className="flex h-full min-h-0 flex-col">
                <ScrollArea className="min-h-0 flex-1">
                  <div className="p-4">{NoteForm}</div>
                </ScrollArea>
              </div>
            ) : mobileTab === 'tasks' ? (
              <div className="h-full">{History}</div>
            ) : (
              <div className="h-full">{Preview}</div>
            )}
          </div>
        </main>

        <nav className="border-t border-white/70 bg-white/95 px-2 pb-[calc(env(safe-area-inset-bottom)+0.5rem)] pt-2 backdrop-blur-sm">
          <div className="grid grid-cols-3 gap-2">
            {mobileTabs.map(tab => {
              const Icon = tab.icon
              const isActive = tab.value === mobileTab

              return (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => setMobileTab(tab.value)}
                  className={cn(
                    'flex min-h-16 flex-col items-center justify-center gap-1 rounded-2xl border px-3 py-2 text-xs font-medium transition-colors',
                    isActive
                      ? 'border-blue-200 bg-blue-50 text-blue-700 shadow-sm'
                      : 'border-transparent bg-transparent text-neutral-500 hover:border-neutral-200 hover:bg-neutral-50 hover:text-neutral-900'
                  )}
                  aria-pressed={isActive}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </nav>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <ResizablePanelGroup direction="horizontal" className="h-full w-full">
        <ResizablePanel
          ref={leftPanelRef}
          defaultSize={23}
          minSize={10}
          maxSize={35}
          collapsible
          collapsedSize={0}
          onCollapse={() => setIsLeftCollapsed(true)}
          onExpand={() => setIsLeftCollapsed(false)}
        >
          <aside className="flex h-full flex-col overflow-hidden border-r border-neutral-200 bg-white">
            <header className="flex h-16 items-center justify-between px-6">
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl">
                  <img src={logo} alt="logo" className="h-full w-full object-contain" />
                </div>
                <div className="text-2xl font-bold text-gray-800">BiliNote</div>
              </div>
              <div className="flex items-center gap-1">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => leftPanelRef.current?.collapse()}
                        className="text-muted-foreground hover:text-primary cursor-pointer rounded p-1 hover:bg-neutral-100"
                      >
                        <PanelLeftClose className="h-5 w-5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <span>收起工作区</span>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link to="/settings">
                        <SlidersHorizontal className="text-muted-foreground hover:text-primary cursor-pointer" />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent>
                      <span>全局配置</span>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </header>
            <ScrollArea className="flex-1 overflow-auto">
              <div className="p-4">{NoteForm}</div>
            </ScrollArea>
          </aside>
        </ResizablePanel>

        <ResizableHandle />

        {isLeftCollapsed && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => leftPanelRef.current?.expand()}
                  className="flex h-full w-8 shrink-0 items-center justify-center border-r border-neutral-200 bg-white hover:bg-neutral-50"
                >
                  <PanelLeftOpen className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <span>展开工作区</span>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        <ResizablePanel
          ref={middlePanelRef}
          defaultSize={16}
          minSize={10}
          maxSize={30}
          collapsible
          collapsedSize={0}
          onCollapse={() => setIsMiddleCollapsed(true)}
          onExpand={() => setIsMiddleCollapsed(false)}
        >
          <aside className="flex h-full flex-col overflow-hidden border-r border-neutral-200 bg-white">
            <header className="flex h-10 shrink-0 items-center justify-between border-b border-neutral-100 px-3">
              <span className="text-sm font-medium text-gray-600">生成历史</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => middlePanelRef.current?.collapse()}
                      className="text-muted-foreground hover:text-primary cursor-pointer rounded p-1 hover:bg-neutral-100"
                    >
                      <PanelLeftClose className="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <span>收起历史</span>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </header>
            <ScrollArea className="flex-1 overflow-auto">
              <div>{History}</div>
            </ScrollArea>
          </aside>
        </ResizablePanel>

        <ResizableHandle />

        {isMiddleCollapsed && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => middlePanelRef.current?.expand()}
                  className="flex h-full w-8 shrink-0 items-center justify-center border-r border-neutral-200 bg-white hover:bg-neutral-50"
                >
                  <HistoryIcon className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <span>展开历史</span>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        <ResizablePanel defaultSize={61} minSize={30}>
          <main className="flex h-full flex-col overflow-hidden bg-white p-6">{Preview}</main>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

export default HomeLayout
