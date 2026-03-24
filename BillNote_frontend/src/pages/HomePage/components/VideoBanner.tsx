import { ExternalLink } from 'lucide-react'

import type { AudioMeta } from '@/store/taskStore'

interface VideoBannerProps {
  audioMeta?: AudioMeta
  videoUrl?: string
}

const platformLabel: Record<string, string> = {
  bilibili: '哔哩哔哩',
  youtube: 'YouTube',
  douyin: '抖音',
  xiaohongshu: '小红书',
}

export default function VideoBanner({ audioMeta, videoUrl }: VideoBannerProps) {
  if (!audioMeta) return null

  const rawInfo = (audioMeta.raw_info ?? {}) as Record<string, unknown>
  const rawCover = audioMeta.cover_url
  const apiBase = String(import.meta.env.VITE_API_BASE_URL || 'api').replace(/\/$/, '')
  const coverUrl = rawCover
    ? rawCover.startsWith('http')
      ? `${apiBase}/image_proxy?url=${encodeURIComponent(rawCover)}`
      : rawCover
    : ''
  const title = audioMeta.title
  const uploader = typeof rawInfo.uploader === 'string' ? rawInfo.uploader : ''
  const platform = platformLabel[audioMeta.platform] || audioMeta.platform || ''
  const originalUrl =
    videoUrl ||
    (typeof rawInfo.webpage_url === 'string' ? rawInfo.webpage_url : '')

  return (
    <div className="relative mb-4 overflow-hidden rounded-lg">
      <div className="absolute inset-0">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt=""
            referrerPolicy="no-referrer"
            className="h-full w-full scale-110 object-cover brightness-[0.4] blur-md"
          />
        ) : (
          <div className="h-full w-full bg-gradient-to-r from-blue-600 to-indigo-700" />
        )}
      </div>

      <div className="relative flex items-center gap-4 px-5 py-4">
        {coverUrl && (
          <img
            src={coverUrl}
            alt={title}
            referrerPolicy="no-referrer"
            className="h-16 w-28 shrink-0 rounded-md object-cover shadow-md"
          />
        )}

        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-bold text-white" title={title}>
            {title}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-white/70">
            {uploader && <span>{uploader}</span>}
            {uploader && platform && <span className="text-white/40">·</span>}
            {platform && <span>{platform}</span>}
          </div>
        </div>

        {originalUrl && (
          <a
            href={originalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex shrink-0 items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/25"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>原视频</span>
          </a>
        )}
      </div>
    </div>
  )
}
