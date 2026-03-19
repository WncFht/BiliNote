import {
  WEB_DEFAULT_NOTE_FORMATS,
  WEB_DEFAULT_NOTE_STYLE,
  WEB_DEFAULT_VIDEO_INTERVAL,
} from './noteRequest.ts'

type TaskStatus =
  | 'PENDING'
  | 'PARSING'
  | 'DOWNLOADING'
  | 'TRANSCRIBING'
  | 'SUMMARIZING'
  | 'SAVING'
  | 'SUCCESS'
  | 'FAILED'

interface AudioMeta {
  cover_url: string
  duration: number
  file_path: string
  platform: string
  raw_info: unknown
  title: string
  video_id: string
}

interface Segment {
  start: number
  end: number
  text: string
}

interface Transcript {
  full_text: string
  language: string
  raw: unknown
  segments: Segment[]
}

interface MarkdownVersion {
  ver_id: string
  content: string
  style: string
  model_name: string
  created_at: string
}

interface TaskFormData {
  video_url: string
  link: undefined | boolean
  screenshot: undefined | boolean
  platform: string
  quality: string
  model_name: string
  provider_id: string
  style?: string
  format?: string[]
  extras?: string
  video_understanding?: boolean
  video_interval?: number
  grid_size?: number[]
}

export interface HistoryTask {
  id: string
  platform: string
  markdown: string | MarkdownVersion[]
  transcript: Transcript
  status: TaskStatus
  message?: string
  audioMeta: AudioMeta
  createdAt: string
  formData: TaskFormData
}

export interface ServerHistoryResult {
  markdown?: string
  transcript?: Partial<Transcript> | null
  audio_meta?: Partial<AudioMeta> | null
}

export interface ServerHistoryItem {
  task_id: string
  platform?: string
  created_at?: string
  status?: TaskStatus
  message?: string
  result?: ServerHistoryResult | null
}

function buildEmptyTranscript(): Transcript {
  return {
    full_text: '',
    language: '',
    raw: null,
    segments: [],
  }
}

function buildEmptyAudioMeta(platform = ''): AudioMeta {
  return {
    cover_url: '',
    duration: 0,
    file_path: '',
    platform,
    raw_info: null,
    title: '',
    video_id: '',
  }
}

function buildDefaultFormData(platform = 'bilibili'): TaskFormData {
  return {
    video_url: '',
    link: false,
    screenshot: false,
    platform,
    quality: 'medium',
    model_name: '',
    provider_id: '',
    style: WEB_DEFAULT_NOTE_STYLE,
    format: [...WEB_DEFAULT_NOTE_FORMATS],
    extras: '',
    video_understanding: false,
    video_interval: WEB_DEFAULT_VIDEO_INTERVAL,
    grid_size: [],
  }
}

function hasMeaningfulFormData(formData: TaskFormData) {
  return Boolean(formData.video_url || formData.model_name || formData.provider_id)
}

function hasRemoteTranscript(transcript: Transcript) {
  return Boolean(transcript.full_text || transcript.language || transcript.segments.length)
}

function hasRemoteAudioMeta(audioMeta: AudioMeta) {
  return Boolean(audioMeta.title || audioMeta.video_id || audioMeta.cover_url || audioMeta.file_path)
}

function mergeMarkdown(current: HistoryTask['markdown'], incoming: HistoryTask['markdown']) {
  if (Array.isArray(current) && current.length > 0) {
    return current
  }

  if (typeof incoming === 'string' && incoming) {
    return incoming
  }

  return current
}

export function mapHistoryItemToTask(item: ServerHistoryItem): HistoryTask {
  const platform = item.result?.audio_meta?.platform || item.platform || 'bilibili'
  const transcript: Transcript = {
    ...buildEmptyTranscript(),
    ...(item.result?.transcript || {}),
  }
  const audioMeta: AudioMeta = {
    ...buildEmptyAudioMeta(platform),
    ...(item.result?.audio_meta || {}),
    platform,
  }

  return {
    id: item.task_id,
    platform,
    markdown: item.result?.markdown || '',
    transcript,
    status: item.status || (item.result ? 'SUCCESS' : 'PENDING'),
    message: item.message || '',
    audioMeta,
    createdAt: item.created_at || '',
    formData: buildDefaultFormData(platform),
  }
}

export function mergeHydratedTasks(existing: HistoryTask[], incoming: HistoryTask[]): HistoryTask[] {
  const merged = new Map(existing.map(task => [task.id, task]))

  for (const incomingTask of incoming) {
    const currentTask = merged.get(incomingTask.id)
    if (!currentTask) {
      merged.set(incomingTask.id, incomingTask)
      continue
    }

    merged.set(incomingTask.id, {
      ...currentTask,
      status: incomingTask.status || currentTask.status,
      message: incomingTask.message || currentTask.message,
      platform: incomingTask.platform || currentTask.platform,
      createdAt: incomingTask.createdAt || currentTask.createdAt,
      markdown: mergeMarkdown(currentTask.markdown, incomingTask.markdown),
      transcript: hasRemoteTranscript(incomingTask.transcript)
        ? incomingTask.transcript
        : currentTask.transcript,
      audioMeta: hasRemoteAudioMeta(incomingTask.audioMeta)
        ? {
            ...currentTask.audioMeta,
            ...incomingTask.audioMeta,
          }
        : currentTask.audioMeta,
      formData: hasMeaningfulFormData(currentTask.formData)
        ? currentTask.formData
        : incomingTask.formData,
    })
  }

  return Array.from(merged.values()).sort(
    (left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
  )
}
