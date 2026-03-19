import test from 'node:test'
import assert from 'node:assert/strict'

import { buildTaskVideoLink } from '../src/lib/videoLink.ts'

test('buildTaskVideoLink returns a Bilibili short link from the video id', () => {
  const link = buildTaskVideoLink({
    platform: 'bilibili',
    audioMeta: {
      video_id: 'BV1ab411c7de',
    },
    formData: {
      video_url: 'https://www.bilibili.com/video/BV1ab411c7de?p=1',
    },
  })

  assert.deepEqual(link, {
    href: 'https://b23.tv/BV1ab411c7de',
    label: 'b23.tv/BV1ab411c7de',
  })
})

test('buildTaskVideoLink returns a YouTube short link from the video id', () => {
  const link = buildTaskVideoLink({
    platform: 'youtube',
    audioMeta: {
      video_id: 'dQw4w9WgXcQ',
    },
    formData: {
      video_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    },
  })

  assert.deepEqual(link, {
    href: 'https://youtu.be/dQw4w9WgXcQ',
    label: 'youtu.be/dQw4w9WgXcQ',
  })
})

test('buildTaskVideoLink falls back to a compact canonical URL for douyin ids', () => {
  const link = buildTaskVideoLink({
    platform: 'douyin',
    audioMeta: {
      video_id: '7481234567890123456',
    },
    formData: {
      video_url: 'https://www.douyin.com/video/7481234567890123456',
    },
  })

  assert.deepEqual(link, {
    href: 'https://www.douyin.com/video/7481234567890123456',
    label: 'douyin.com/video/7481234567890123456',
  })
})

test('buildTaskVideoLink falls back to the original URL when no compact form is available', () => {
  const link = buildTaskVideoLink({
    platform: 'kuaishou',
    audioMeta: {
      video_id: '',
    },
    formData: {
      video_url: 'https://www.kuaishou.com/short-video/3x7y9z?shareToken=abcdef',
    },
  })

  assert.deepEqual(link, {
    href: 'https://www.kuaishou.com/short-video/3x7y9z?shareToken=abcdef',
    label: 'kuaishou.com/short-video/3x7y9z',
  })
})

test('buildTaskVideoLink returns null for local tasks without a public URL', () => {
  const link = buildTaskVideoLink({
    platform: 'local',
    audioMeta: {
      video_id: '',
    },
    formData: {
      video_url: '/Users/demo/video.mp4',
    },
  })

  assert.equal(link, null)
})
