import test from 'node:test'
import assert from 'node:assert/strict'

import { getProviderBadge } from '../src/lib/providerLogo.ts'

test('getProviderBadge returns stable badges for built-in providers', () => {
  assert.deepEqual(getProviderBadge('OpenAI'), {
    label: 'OA',
    tone: 'emerald',
  })
  assert.deepEqual(getProviderBadge('DeepSeek'), {
    label: 'DS',
    tone: 'sky',
  })
  assert.deepEqual(getProviderBadge('Claude'), {
    label: 'CL',
    tone: 'amber',
  })
})

test('getProviderBadge falls back to initials for unknown providers', () => {
  assert.deepEqual(getProviderBadge('Moonshot AI'), {
    label: 'MO',
    tone: 'slate',
  })
  assert.deepEqual(getProviderBadge(''), {
    label: 'AI',
    tone: 'slate',
  })
})
