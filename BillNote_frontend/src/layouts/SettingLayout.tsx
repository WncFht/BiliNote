import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip.tsx'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { ChevronLeft, House, SlidersHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import logo from '@/assets/icon.svg'
import { getHomeLayoutMode } from '@/lib/homeLayout.ts'
import { getSettingsPageMeta } from '@/lib/settingsLayout.ts'

interface ISettingLayoutProps {
  Menu: React.ReactNode
}

const getInitialLayoutMode = () => {
  if (typeof window === 'undefined') {
    return 'desktop' as const
  }

  return getHomeLayoutMode(window.innerWidth)
}

const SettingLayout = ({ Menu }: ISettingLayoutProps) => {
  const location = useLocation()
  const [layoutMode, setLayoutMode] = useState(getInitialLayoutMode)
  const pageMeta = getSettingsPageMeta(location.pathname)

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

  if (layoutMode === 'mobile') {
    return (
      <div className="flex min-h-screen h-dvh flex-col overflow-hidden bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_55%,#f8fafc_100%)]">
        <header className="border-b border-white/70 bg-white/92 px-4 pb-3 pt-4 backdrop-blur-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-neutral-100 shadow-sm">
                <img src={logo} alt="logo" className="h-full w-full object-contain" />
              </div>
              <div className="min-w-0">
                <div className="text-[11px] font-semibold tracking-[0.24em] text-neutral-400 uppercase">
                  Settings
                </div>
                <div className="truncate text-xl font-semibold text-neutral-900">{pageMeta.title}</div>
                <p className="mt-1 text-xs leading-5 text-neutral-500">{pageMeta.description}</p>
              </div>
            </div>

            <Link
              to="/"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-neutral-200 bg-white text-neutral-500 shadow-sm transition-colors hover:text-neutral-900"
            >
              <House className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {pageMeta.backToHub && (
              <Link
                to="/settings"
                className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700 shadow-sm"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                返回设置中心
              </Link>
            )}
            <Link
              to="/settings/about"
              className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700 shadow-sm"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              查看说明
            </Link>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-hidden px-3 py-3">
          <div className="h-full overflow-hidden rounded-[28px] border border-white/70 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
            <Outlet />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div
      className="h-full w-full"
      style={{
        backgroundColor: 'var(--color-muted)',
      }}
    >
      <div className="flex flex-1">
        {/* 左侧部分：Header + 表单 */}
        <aside className="flex w-[300px] flex-col border-r border-neutral-200 bg-white">
          {/* Header */}
          <header className="flex h-16 items-center justify-between px-6">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl">
                <img src={logo} alt="logo" className="h-full w-full object-contain" />
              </div>
              <div className="text-2xl font-bold text-gray-800">BiliNote</div>
            </div>
            <div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Link to={'/'}>
                      <SlidersHorizontal className="text-muted-foreground hover:text-primary cursor-pointer" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent>
                    <span>返回首页</span>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </header>

          {/* 表单内容 */}
          <div className="flex-1 overflow-auto p-4">
            {/*<NoteForm />*/}
            {Menu}
          </div>
        </aside>

        {/* 右侧预览区域 */}
        <main className="h-screen flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
export default SettingLayout
