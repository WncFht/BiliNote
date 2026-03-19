import './App.css'
import { useTaskPolling } from '@/hooks/useTaskPolling.ts'
import { Suspense, lazy, useEffect } from 'react'
import { BrowserRouter, Routes } from 'react-router-dom'
import { Route } from 'react-router-dom'
import Index from '@/pages/Index.tsx'
import { useCheckBackend } from '@/hooks/useCheckBackend.ts'
import BackendInitDialog from '@/components/BackendInitDialog'
import { useTaskStore } from '@/store/taskStore'
import { startTaskHistoryRefresh } from '@/lib/historySync.ts'

import { HomePage } from './pages/HomePage/Home.tsx'

const SettingPage = lazy(() => import('./pages/SettingPage/index.tsx'))
const Model = lazy(() => import('./pages/SettingPage/Model.tsx'))
const ProviderForm = lazy(() => import('@/components/Form/modelForm/Form.tsx'))
const Downloader = lazy(() => import('./pages/SettingPage/Downloader.tsx'))
const DownloaderForm = lazy(() => import('@/components/Form/DownloaderForm/Form.tsx'))
const SettingsIndex = lazy(() => import('@/pages/SettingPage/SettingsIndex.tsx'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

const RouteLoader = () => (
  <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_55%,#f8fafc_100%)] px-6 text-center text-sm text-neutral-500">
    正在载入页面…
  </div>
)

function App() {
  useTaskPolling(3000) // 每 3 秒轮询一次
  const { loading, initialized } = useCheckBackend()
  const loadTaskHistory = useTaskStore(state => state.loadTaskHistory)

  // 首屏优先保持可交互，历史列表改为在浏览器空闲时同步。
  useEffect(() => {
    if (!initialized) {
      return
    }

    let cancelled = false

    const hydrateTaskHistory = () => {
      if (cancelled) {
        return
      }

      void loadTaskHistory().catch(error => {
        console.warn('加载任务历史失败', error)
      })
    }

    let idleHandle: number | null = null
    let timeoutHandle: number | null = null

    if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
      idleHandle = window.requestIdleCallback(hydrateTaskHistory, { timeout: 1500 })
    } else if (typeof window !== 'undefined') {
      timeoutHandle = window.setTimeout(hydrateTaskHistory, 400)
    }

    const stopTaskHistoryRefresh = startTaskHistoryRefresh(hydrateTaskHistory)

    return () => {
      cancelled = true
      stopTaskHistoryRefresh()

      if (idleHandle !== null && typeof window.cancelIdleCallback === 'function') {
        window.cancelIdleCallback(idleHandle)
      }

      if (timeoutHandle !== null) {
        window.clearTimeout(timeoutHandle)
      }
    }
  }, [initialized, loadTaskHistory])

  // 如果后端还未初始化，显示初始化对话框
  if (!initialized) {
    return (
      <>
        <BackendInitDialog open={loading} />
      </>
    )
  }

  // 后端已初始化，渲染主应用
  return (
    <>
      <BrowserRouter>
        <Suspense fallback={<RouteLoader />}>
          <Routes>
            <Route path="/" element={<Index />}>
              <Route index element={<HomePage />} />
              <Route path="settings" element={<SettingPage />}>
                <Route index element={<SettingsIndex />} />
                <Route path="model" element={<Model />}>
                  <Route path="new" element={<ProviderForm isCreate />} />
                  <Route path=":id" element={<ProviderForm />} />
                </Route>
                <Route path="download" element={<Downloader />}>
                  <Route path=":id" element={<DownloaderForm />} />
                </Route>
                <Route path="*" element={<NotFoundPage />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </>
  )
}

export default App
