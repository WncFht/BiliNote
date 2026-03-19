export const WEB_DEFAULT_NOTE_FORMATS = ['toc', 'summary'] as const
export const WEB_DEFAULT_NOTE_STYLE = 'detailed'
export const WEB_DEFAULT_VIDEO_INTERVAL = 4

export const WEB_NOTE_FORMATS = [
  { label: '目录', value: 'toc' },
  { label: '原片跳转', value: 'link' },
  { label: 'AI总结', value: 'summary' },
] as const

type ImageInputFields = {
  format?: string[]
  screenshot?: boolean
  video_understanding?: boolean
  video_interval?: number
  grid_size?: number[]
}

export function buildDefaultWebNoteFormValues(modelName = '') {
  return {
    platform: 'bilibili',
    quality: 'medium' as const,
    model_name: modelName,
    style: WEB_DEFAULT_NOTE_STYLE,
    format: [...WEB_DEFAULT_NOTE_FORMATS],
    screenshot: false,
    link: false,
    video_understanding: false,
    video_interval: WEB_DEFAULT_VIDEO_INTERVAL,
    grid_size: [] as number[],
  }
}

export function normalizeWebGenerateNotePayload<T extends ImageInputFields>(payload: T) {
  const rawFormat = payload.format === undefined ? [...WEB_DEFAULT_NOTE_FORMATS] : payload.format
  const format = Array.from(new Set((rawFormat || []).filter(item => item !== 'screenshot')))

  return {
    ...payload,
    format,
    screenshot: false,
    video_understanding: false,
    video_interval: WEB_DEFAULT_VIDEO_INTERVAL,
    grid_size: [] as number[],
  }
}
