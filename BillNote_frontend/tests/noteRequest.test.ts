import test from 'node:test'
import assert from 'node:assert/strict'

import {
  WEB_NOTE_FORMATS,
  buildDefaultWebNoteFormValues,
  normalizeWebGenerateNotePayload,
} from '../src/lib/noteRequest.ts'

test('web defaults prefer stable text-only note generation', () => {
  const defaults = buildDefaultWebNoteFormValues('gpt-5.4')

  assert.equal(defaults.model_name, 'gpt-5.4')
  assert.equal(defaults.style, 'detailed')
  assert.deepEqual(defaults.format, ['toc', 'summary'])
  assert.equal(defaults.screenshot, false)
  assert.equal(defaults.video_understanding, false)
  assert.equal(defaults.video_interval, 4)
  assert.deepEqual(defaults.grid_size, [])
})

test('normalizeWebGenerateNotePayload strips image-input fields before sending web requests', () => {
  const payload = normalizeWebGenerateNotePayload({
    video_url: 'https://www.bilibili.com/video/BV19CwVz7EAU',
    platform: 'bilibili',
    quality: 'medium',
    model_name: 'gpt-5.4',
    provider_id: 'openai',
    style: 'detailed',
    format: ['toc', 'summary', 'screenshot'],
    screenshot: true,
    link: true,
    extras: 'focus on valuation logic',
    video_understanding: true,
    video_interval: 8,
    grid_size: [3, 3],
  })

  assert.deepEqual(payload.format, ['toc', 'summary'])
  assert.equal(payload.screenshot, false)
  assert.equal(payload.video_understanding, false)
  assert.equal(payload.video_interval, 4)
  assert.deepEqual(payload.grid_size, [])
  assert.equal(payload.link, true)
  assert.equal(payload.extras, 'focus on valuation logic')
})

test('web note formats hide the screenshot option', () => {
  assert.equal(WEB_NOTE_FORMATS.some(item => item.value === 'screenshot'), false)
})
