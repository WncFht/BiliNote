import { useEffect, useRef } from 'react'
import { get_task_status } from '@/services/note.ts'
import { useTaskStore } from '@/store/taskStore'
import { buildPollingTaskPatch } from '@/lib/taskProgress.ts'
import toast from 'react-hot-toast'

export const useTaskPolling = (interval = 3000) => {
  const tasks = useTaskStore(state => state.tasks)
  const updateTaskContent = useTaskStore(state => state.updateTaskContent)

  const tasksRef = useRef(tasks)

  // 每次 tasks 更新，把最新的 tasks 同步进去
  useEffect(() => {
    tasksRef.current = tasks
  }, [tasks])

  useEffect(() => {
    const timer = setInterval(async () => {
      const pendingTasks = tasksRef.current.filter(
        task => task.status != 'SUCCESS' && task.status != 'FAILED'
      )

      for (const task of pendingTasks) {
        try {
          console.log('🔄 正在轮询任务：', task.id)
          const res = await get_task_status(task.id)
          const patch = buildPollingTaskPatch(
            {
              status: task.status,
              message: task.message,
            },
            res
          )

          if (patch) {
            if (patch.status === 'SUCCESS') {
              toast.success('笔记生成成功')
              updateTaskContent(task.id, patch)
            } else if (patch.status === 'FAILED') {
              updateTaskContent(task.id, patch)
              console.warn(`⚠️ 任务 ${task.id} 失败`)
            } else {
              updateTaskContent(task.id, patch)
            }
          }
        } catch (e) {
          console.error('❌ 任务轮询失败：', e)
          // toast.error(`生成失败 ${e.message || e}`)
          updateTaskContent(task.id, { status: 'FAILED', message: '任务轮询失败，请检查后端服务' })
        }
      }
    }, interval)

    return () => clearInterval(timer)
  }, [interval, updateTaskContent])
}
