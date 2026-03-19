import test from 'node:test'
import assert from 'node:assert/strict'

import { mapHistoryItemToTask, mergeHydratedTasks } from '../src/lib/historySync.ts'

test('mapHistoryItemToTask converts backend history payload to frontend task shape', () => {
  const task = mapHistoryItemToTask({
    task_id: 'task-1',
    platform: 'bilibili',
    created_at: '2026-03-19T18:20:00',
    status: 'SUCCESS',
    message: 'done',
    result: {
      markdown: '# Title',
      transcript: {
        full_text: 'hello',
        language: 'zh',
        raw: null,
        segments: [],
      },
      audio_meta: {
        cover_url: 'https://example.com/cover.jpg',
        duration: 12,
        file_path: '/tmp/audio.mp3',
        platform: 'bilibili',
        raw_info: {},
        title: 'Example title',
        video_id: 'BV1',
      },
    },
  })

  assert.equal(task.id, 'task-1')
  assert.equal(task.status, 'SUCCESS')
  assert.equal(task.audioMeta.title, 'Example title')
  assert.equal(task.formData.platform, 'bilibili')
  assert.equal(task.markdown, '# Title')
})

test('mergeHydratedTasks preserves local formData while accepting remote result data', () => {
  const merged = mergeHydratedTasks(
    [
      {
        id: 'task-1',
        status: 'PENDING',
        message: '任务排队中',
        markdown: '',
        createdAt: '2026-03-19T18:20:00',
        transcript: {
          full_text: '',
          language: '',
          raw: null,
          segments: [],
        },
        audioMeta: {
          cover_url: '',
          duration: 0,
          file_path: '',
          platform: 'bilibili',
          raw_info: null,
          title: '',
          video_id: '',
        },
        formData: {
          video_url: 'https://www.bilibili.com/video/BV1',
          link: true,
          screenshot: false,
          platform: 'bilibili',
          quality: 'medium',
          model_name: 'gpt-5.4',
          provider_id: 'provider-1',
          format: ['toc', 'summary'],
          style: 'detailed',
        },
      },
    ],
    [
      mapHistoryItemToTask({
        task_id: 'task-1',
        platform: 'bilibili',
        created_at: '2026-03-19T18:20:00',
        status: 'SUCCESS',
        message: 'done',
        result: {
          markdown: '# Title',
          transcript: {
            full_text: 'hello',
            language: 'zh',
            raw: null,
            segments: [],
          },
          audio_meta: {
            cover_url: 'https://example.com/cover.jpg',
            duration: 12,
            file_path: '/tmp/audio.mp3',
            platform: 'bilibili',
            raw_info: {},
            title: 'Example title',
            video_id: 'BV1',
          },
        },
      }),
    ]
  )

  assert.equal(merged.length, 1)
  assert.equal(merged[0].status, 'SUCCESS')
  assert.equal(merged[0].markdown, '# Title')
  assert.equal(merged[0].audioMeta.title, 'Example title')
  assert.equal(merged[0].formData.video_url, 'https://www.bilibili.com/video/BV1')
  assert.equal(merged[0].formData.model_name, 'gpt-5.4')
})
