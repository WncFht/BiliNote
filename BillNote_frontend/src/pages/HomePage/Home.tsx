import { FC, Suspense, lazy, useEffect, useState } from 'react'
import HomeLayout from '@/layouts/HomeLayout.tsx'
import NoteForm from '@/pages/HomePage/components/NoteForm.tsx'
import { useTaskStore } from '@/store/taskStore'
import { deriveViewStatus, type ViewStatus } from '@/lib/taskProgress.ts'

const MarkdownViewer = lazy(() => import('@/pages/HomePage/components/MarkdownViewer.tsx'))
const History = lazy(() => import('@/pages/HomePage/components/History.tsx'))

const PreviewLoader = ({ status }: { status: ViewStatus }) => (
  <div className="flex h-full min-h-0 w-full flex-col items-center justify-center gap-4 px-6 text-center text-neutral-500">
    <div className="grid gap-2">
      <div className="mx-auto h-3 w-24 animate-pulse rounded-full bg-neutral-200" />
      <div className="mx-auto h-3 w-36 animate-pulse rounded-full bg-neutral-100" />
    </div>
    <div>
      <p className="text-sm font-medium text-neutral-800">
        {status === 'idle' ? '正在准备预览模块' : '正在载入笔记预览'}
      </p>
      <p className="mt-1 text-xs text-neutral-500">
        预览面板已改为按需加载，移动端首屏会优先保证表单可操作。
      </p>
    </div>
  </div>
)

const HistoryLoader = () => (
  <div className="flex h-full min-h-0 items-center justify-center px-6 text-sm text-neutral-500">
    正在载入历史记录…
  </div>
)

export const HomePage: FC = () => {
  const tasks = useTaskStore(state => state.tasks)
  const currentTaskId = useTaskStore(state => state.currentTaskId)

  const currentTask = tasks.find(t => t.id === currentTaskId)

  const [status, setStatus] = useState<ViewStatus>('idle')

  useEffect(() => {
    setStatus(deriveViewStatus(currentTask?.status))
  }, [currentTask])

  // useEffect( () => {
  //     get_task_status('d4e87938-c066-48a0-bbd5-9bec40d53354').then(res=>{
  //         console.log('res1',res)
  //         setContent(res.data.result.markdown)
  //     })
  // }, [tasks]);
  return (
    <HomeLayout
      NoteForm={<NoteForm />}
      Preview={
        <Suspense fallback={<PreviewLoader status={status} />}>
          <MarkdownViewer status={status} />
        </Suspense>
      }
      History={
        <Suspense fallback={<HistoryLoader />}>
          <History />
        </Suspense>
      }
    />
  )
}
