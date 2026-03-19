import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildSettingsHubCards,
  getSettingsIndexTarget,
  getSettingsPageMeta,
} from '../src/lib/settingsLayout.ts'

test('desktop settings index redirects to model while mobile stays on hub', () => {
  assert.equal(getSettingsIndexTarget(1280), '/settings/model')
  assert.equal(getSettingsIndexTarget(768), '/settings/model')
  assert.equal(getSettingsIndexTarget(390), null)
})

test('settings page metadata marks root as hub and details as back-navigable', () => {
  assert.deepEqual(getSettingsPageMeta('/settings'), {
    title: '设置中心',
    description: '浏览配置摘要与说明',
    backToHub: false,
  })

  assert.deepEqual(getSettingsPageMeta('/settings/model'), {
    title: '模型设置',
    description: '查看供应商与已启用模型',
    backToHub: true,
  })

  assert.deepEqual(getSettingsPageMeta('/settings/download/123'), {
    title: '下载配置',
    description: '查看支持平台与 Cookie 设置',
    backToHub: true,
  })
})

test('settings hub cards expose readable summaries and stable destinations', () => {
  const cards = buildSettingsHubCards({
    providerCount: 2,
    enabledProviderCount: 1,
    enabledModelCount: 3,
    downloadPlatformCount: 4,
  })

  assert.equal(cards.length, 3)
  assert.deepEqual(cards.map(card => card.path), [
    '/settings/model',
    '/settings/download',
    '/settings/about',
  ])
  assert.match(cards[0].summary, /3/)
  assert.match(cards[0].detail, /2/)
  assert.match(cards[1].summary, /4/)
  assert.match(cards[2].summary, /BiliNote/)
})

test('settings hub cards fall back to neutral copy when data is missing', () => {
  const cards = buildSettingsHubCards({
    providerCount: 0,
    enabledProviderCount: 0,
    enabledModelCount: 0,
    downloadPlatformCount: 0,
  })

  assert.match(cards[0].summary, /尚未/)
  assert.match(cards[1].summary, /支持平台/)
})
