import { useEffect, useRef } from 'react'
import toast from 'react-hot-toast'

import { get_task_status } from '@/services/note.ts'
import { useTaskStore } from '@/store/taskStore'
import { buildPollingTaskPatch } from '@/lib/taskProgress.ts'

export const useTaskPolling = (interval = 3000) => {
  const tasks = useTaskStore(state => state.tasks)
  const updateTaskContent = useTaskStore(state => state.updateTaskContent)

  const tasksRef = useRef(tasks)

  useEffect(() => {
    tasksRef.current = tasks
  }, [tasks])

  useEffect(() => {
    const timer = setInterval(async () => {
      const pendingTasks = tasksRef.current.filter(
        task => task.status !== 'SUCCESS' && task.status !== 'FAILED'
      )

      for (const task of pendingTasks) {
        try {
          const res = await get_task_status(task.id)
          const patch = buildPollingTaskPatch(
            {
              status: task.status,
              message: task.message,
            },
            res
          )

          if (!patch) {
            continue
          }

          updateTaskContent(task.id, patch)

          if (patch.status === 'SUCCESS') {
            toast.success('笔记生成成功')
          } else if (patch.status === 'FAILED') {
            console.warn(`⚠️ 任务 ${task.id} 失败`)
          }
        } catch (error) {
          console.error('❌ 任务轮询失败：', error)
          updateTaskContent(task.id, {
            status: 'FAILED',
            message: '任务轮询失败，请检查后端服务',
          })
        }
      }
    }, interval)

    return () => clearInterval(timer)
  }, [interval, updateTaskContent])
}
