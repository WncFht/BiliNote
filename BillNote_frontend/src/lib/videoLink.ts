export interface TaskVideoLinkSource {
  platform?: string
  audioMeta?: {
    video_id?: string | null
  }
  formData?: {
    video_url?: string | null
  }
}

export interface TaskVideoLink {
  href: string
  label: string
}

function extractBilibiliId(url: string) {
  const match = url.match(/BV([0-9A-Za-z]+)/)
  return match ? `BV${match[1]}` : ''
}

function extractYouTubeId(url: string) {
  const match = url.match(/(?:v=|youtu\.be\/)([0-9A-Za-z_-]{11})/)
  return match?.[1] || ''
}

function extractDouyinId(url: string) {
  const match = url.match(/\/video\/(\d+)/)
  return match?.[1] || ''
}

function buildCompactLabel(href: string) {
  try {
    const parsed = new URL(href)
    const host = parsed.hostname.replace(/^www\./, '')
    const pathname = parsed.pathname.replace(/\/+$/, '') || '/'
    return `${host}${pathname}`
  } catch {
    return href.replace(/^https?:\/\//, '')
  }
}

function buildFallbackVideoLink(rawUrl: string): TaskVideoLink | null {
  if (!rawUrl) {
    return null
  }

  try {
    const parsed = new URL(rawUrl)
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return null
    }

    return {
      href: rawUrl,
      label: buildCompactLabel(rawUrl),
    }
  } catch {
    return null
  }
}

export function buildTaskVideoLink(source: TaskVideoLinkSource): TaskVideoLink | null {
  const platform = source.platform || ''
  const rawUrl = source.formData?.video_url?.trim() || ''

  if (platform === 'local') {
    return null
  }

  const videoId = source.audioMeta?.video_id?.trim() || ''

  if (platform === 'bilibili') {
    const resolvedId = videoId || extractBilibiliId(rawUrl)
    if (resolvedId) {
      const href = `https://b23.tv/${resolvedId}`
      return {
        href,
        label: buildCompactLabel(href),
      }
    }
  }

  if (platform === 'youtube') {
    const resolvedId = videoId || extractYouTubeId(rawUrl)
    if (resolvedId) {
      const href = `https://youtu.be/${resolvedId}`
      return {
        href,
        label: buildCompactLabel(href),
      }
    }
  }

  if (platform === 'douyin') {
    const resolvedId = videoId || extractDouyinId(rawUrl)
    if (resolvedId) {
      const href = `https://www.douyin.com/video/${resolvedId}`
      return {
        href,
        label: buildCompactLabel(href),
      }
    }
  }

  return buildFallbackVideoLink(rawUrl)
}
