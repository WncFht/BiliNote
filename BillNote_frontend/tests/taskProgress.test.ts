import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildPollingTaskPatch,
  buildTaskProgressDisplay,
  deriveViewStatus,
} from '../src/lib/taskProgress.ts'

test('buildPollingTaskPatch updates when status message changes under same status', () => {
  const patch = buildPollingTaskPatch(
    {
      status: 'SUMMARIZING',
      message: '总结中：模型正在生成',
    },
    {
      status: 'SUMMARIZING',
      message: '总结中：已生成约 401 字',
    }
  )

  assert.deepEqual(patch, {
    status: 'SUMMARIZING',
    message: '总结中：已生成约 401 字',
  })
})

test('buildPollingTaskPatch returns null when status and message are unchanged', () => {
  const patch = buildPollingTaskPatch(
    {
      status: 'DOWNLOADING',
      message: '下载中',
    },
    {
      status: 'DOWNLOADING',
      message: '下载中',
    }
  )

  assert.equal(patch, null)
})

test('buildTaskProgressDisplay prefers backend progress message', () => {
  const display = buildTaskProgressDisplay('SUMMARIZING', '总结中：已生成约 401 字')

  assert.equal(display.title, '正在生成笔记，请稍候…')
  assert.equal(display.detail, '总结中：已生成约 401 字')
})

test('buildTaskProgressDisplay falls back to a status-specific message', () => {
  const display = buildTaskProgressDisplay('TRANSCRIBING', '')

  assert.equal(display.detail, '正在转写音频内容')
})

test('deriveViewStatus treats all in-progress task states as loading', () => {
  assert.equal(deriveViewStatus(undefined), 'idle')
  assert.equal(deriveViewStatus('PENDING'), 'loading')
  assert.equal(deriveViewStatus('PARSING'), 'loading')
  assert.equal(deriveViewStatus('SUMMARIZING'), 'loading')
  assert.equal(deriveViewStatus('SUCCESS'), 'success')
  assert.equal(deriveViewStatus('FAILED'), 'failed')
})
