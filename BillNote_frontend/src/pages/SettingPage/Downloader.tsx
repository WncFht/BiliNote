import { Outlet, useLocation } from 'react-router-dom'
import Options from '@/components/Form/DownloaderForm/Options.tsx'
import { Badge } from '@/components/ui/badge.tsx'
import { videoPlatforms } from '@/constant/note.ts'

const Downloader = () => {
  const location = useLocation()
  const downloadPlatformCount = videoPlatforms.filter(platform => platform.value !== 'local').length
  const showDetail = location.pathname !== '/settings/download'

  return (
    <div className="flex h-full min-h-0 flex-col bg-white md:flex-row">
      <div className="border-b border-neutral-200 p-3 md:hidden">
        <div className="rounded-3xl border border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.95),rgba(255,255,255,0.95))] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="bg-white text-emerald-700">
              下载配置
            </Badge>
            <Badge variant="secondary" className="bg-white text-neutral-700">
              {downloadPlatformCount} 个平台
            </Badge>
          </div>
          <p className="mt-3 text-sm font-medium text-neutral-800">
            按平台维护 Cookie，手机上先看平台入口和说明，再进入单个平台编辑。
          </p>
          <p className="mt-2 text-xs leading-5 text-neutral-500">
            这能避免在窄屏里直接铺开长表单。
          </p>
        </div>
      </div>

      <div className="min-h-0 w-full border-b border-neutral-200 p-3 md:w-[320px] md:shrink-0 md:border-b-0 md:border-r">
        <Options />
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {showDetail ? (
          <Outlet />
        ) : (
          <div className="flex h-full items-center justify-center px-6 py-8">
            <div className="max-w-md rounded-[28px] border border-neutral-200 bg-white p-6 text-center shadow-sm">
              <h2 className="text-xl font-semibold text-neutral-900">选择平台后再编辑 Cookie</h2>
              <p className="mt-3 text-sm leading-6 text-neutral-500">
                先从左侧列表点进具体平台，手机端阅读路径会比直接进入表单更清晰。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
export default Downloader
