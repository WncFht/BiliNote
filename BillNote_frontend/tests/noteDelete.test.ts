import test from 'node:test'
import assert from 'node:assert/strict'

import { buildDeleteTaskPayload } from '../src/lib/deleteTaskRequest.ts'

test('buildDeleteTaskPayload keeps task_id for backend deletion', () => {
  assert.deepEqual(
    buildDeleteTaskPayload({
      task_id: 'task-1',
      video_id: 'BV1',
      platform: 'bilibili',
    }),
    {
      task_id: 'task-1',
      video_id: 'BV1',
      platform: 'bilibili',
    }
  )
})
