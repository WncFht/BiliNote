import './App.css'
import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import BackendInitDialog from '@/components/BackendInitDialog'
import { useCheckBackend } from '@/hooks/useCheckBackend.ts'
import { useTaskPolling } from '@/hooks/useTaskPolling.ts'
import { startTaskHistoryRefresh } from '@/lib/historySync.ts'
import Index from '@/pages/Index.tsx'
import { HomePage } from '@/pages/HomePage/Home.tsx'
import { systemCheck } from '@/services/system.ts'
import { useTaskStore } from '@/store/taskStore'

const SettingPage = lazy(() => import('@/pages/SettingPage/index.tsx'))
const Model = lazy(() => import('@/pages/SettingPage/Model.tsx'))
const ProviderForm = lazy(() => import('@/components/Form/modelForm/Form.tsx'))
const Downloader = lazy(() => import('@/pages/SettingPage/Downloader.tsx'))
const DownloaderForm = lazy(() => import('@/components/Form/DownloaderForm/Form.tsx'))
const SettingsIndex = lazy(() => import('@/pages/SettingPage/SettingsIndex.tsx'))
const TranscriberPage = lazy(() => import('@/pages/SettingPage/transcriber.tsx'))
const Monitor = lazy(() => import('@/pages/SettingPage/Monitor.tsx'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

const RouteLoader = () => (
  <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_55%,#f8fafc_100%)] px-6 text-center text-sm text-neutral-500">
    正在载入页面…
  </div>
)

function App() {
  useTaskPolling(3000)
  const { loading, initialized } = useCheckBackend()
  const loadTaskHistory = useTaskStore(state => state.loadTaskHistory)

  useEffect(() => {
    if (!initialized) {
      return
    }

    void systemCheck().catch(error => {
      console.warn('系统检查失败', error)
    })

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

  if (!initialized) {
    return <BackendInitDialog open={loading} />
  }

  return (
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
              <Route path="transcriber" element={<TranscriberPage />} />
              <Route path="monitor" element={<Monitor />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
