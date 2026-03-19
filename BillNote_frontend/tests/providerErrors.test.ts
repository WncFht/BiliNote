import test from 'node:test'
import assert from 'node:assert/strict'

import { getProviderTestErrorMessage } from '../src/lib/providerErrors.ts'

test('getProviderTestErrorMessage reads a backend envelope message', () => {
  assert.equal(
    getProviderTestErrorMessage({
      msg: 'API Key 无效',
    }),
    'API Key 无效'
  )
})

test('getProviderTestErrorMessage falls back to generic Error messages', () => {
  assert.equal(getProviderTestErrorMessage(new Error('network boom')), 'network boom')
})

test('getProviderTestErrorMessage returns a stable fallback for unknown shapes', () => {
  assert.equal(getProviderTestErrorMessage({}), '未知错误')
})
