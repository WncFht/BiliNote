import test from 'node:test'
import assert from 'node:assert/strict'

import {
  MOBILE_HOME_BREAKPOINT,
  getDefaultMobileHomeTab,
  getHomeLayoutMode,
  getSyncedMobileHomeTab,
} from '../src/lib/homeLayout.ts'

test('getHomeLayoutMode switches to mobile below the breakpoint', () => {
  assert.equal(MOBILE_HOME_BREAKPOINT, 768)
  assert.equal(getHomeLayoutMode(375), 'mobile')
  assert.equal(getHomeLayoutMode(767), 'mobile')
  assert.equal(getHomeLayoutMode(768), 'desktop')
})

test('getDefaultMobileHomeTab starts new sessions on create', () => {
  assert.equal(getDefaultMobileHomeTab(null), 'create')
  assert.equal(getDefaultMobileHomeTab('task-1'), 'preview')
})

test('getSyncedMobileHomeTab routes task changes into the right mobile tab', () => {
  assert.equal(getSyncedMobileHomeTab('tasks', null, 'task-1'), 'preview')
  assert.equal(getSyncedMobileHomeTab('preview', 'task-1', null), 'create')
  assert.equal(getSyncedMobileHomeTab('tasks', 'task-1', 'task-1'), 'tasks')
})
