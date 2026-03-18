export type TaskProcessingStatus =
  | 'PENDING'
  | 'PARSING'
  | 'DOWNLOADING'
  | 'TRANSCRIBING'
  | 'SUMMARIZING'
  | 'SAVING'
  | 'SUCCESS'
  | 'FAILED'

export type ViewStatus = 'idle' | 'loading' | 'success' | 'failed'

export interface TaskProgressSnapshot {
  status?: string | null
  message?: string | null
}

export interface TaskStatusResultPayload {
  markdown?: string
  transcript?: unknown
  audio_meta?: unknown
}

export interface TaskStatusResponsePayload {
  status?: string | null
  message?: string | null
  result?: TaskStatusResultPayload | null
}

const statusMessages: Record<string, string> = {
  PENDING: '任务排队中',
  PARSING: '正在解析视频链接',
  DOWNLOADING: '正在下载音频或视频资源',
  TRANSCRIBING: '正在转写音频内容',
  SUMMARIZING: '正在总结视频内容',
  SAVING: '正在保存笔记结果',
}

export function deriveViewStatus(status?: string | null): ViewStatus {
  if (!status) {
    return 'idle'
  }

  if (status === 'SUCCESS') {
    return 'success'
  }

  if (status === 'FAILED') {
    return 'failed'
  }

  return 'loading'
}

export function buildTaskProgressDisplay(status?: string | null, message?: string | null) {
  return {
    title: '正在生成笔记，请稍候…',
    detail: (message || '').trim() || statusMessages[status || ''] || '任务正在处理中',
    hint: '这可能需要几秒钟时间，取决于视频长度',
  }
}

export function buildPollingTaskPatch(
  currentTask: TaskProgressSnapshot,
  response: TaskStatusResponsePayload
) {
  const nextStatus = response.status
  if (!nextStatus) {
    return null
  }

  const nextMessage = response.message ?? ''
  const currentMessage = currentTask.message ?? ''
  const statusChanged = nextStatus !== currentTask.status
  const messageChanged = nextMessage !== currentMessage

  if (!statusChanged && !messageChanged) {
    return null
  }

  const patch: Record<string, unknown> = {
    status: nextStatus,
    message: nextMessage,
  }

  if (nextStatus === 'SUCCESS' && response.result) {
    patch.markdown = response.result.markdown
    patch.transcript = response.result.transcript
    patch.audioMeta = response.result.audio_meta
  }

  return patch
}
