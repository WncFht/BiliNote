import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveProviderIdForModel } from '../src/lib/noteSubmission.ts'

test('resolveProviderIdForModel returns the matched provider id', () => {
  assert.equal(
    resolveProviderIdForModel(
      [
        { provider_id: 'provider-1', model_name: 'gpt-5.4' },
        { provider_id: 'provider-2', model_name: 'deepseek-chat' },
      ],
      'gpt-5.4'
    ),
    'provider-1'
  )
})

test('resolveProviderIdForModel throws when the selected model is stale', () => {
  assert.throws(
    () => resolveProviderIdForModel([], 'gpt-5.4'),
    /当前模型不可用，请刷新模型列表后重试/
  )
})
