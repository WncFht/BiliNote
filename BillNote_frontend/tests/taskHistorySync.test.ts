import test from 'node:test'
import assert from 'node:assert/strict'

import * as historySync from '../src/lib/historySync.ts'

test('startTaskHistoryRefresh keeps remote history in sync while the page stays open', () => {
  let visibilityState: 'visible' | 'hidden' = 'visible'
  let intervalCallback: (() => void) | null = null
  let clearedIntervalId: number | null = null

  const windowListeners = new Map<string, () => void>()
  const documentListeners = new Map<string, () => void>()
  const syncCalls: string[] = []

  assert.equal(typeof historySync.startTaskHistoryRefresh, 'function')

  const stopSync = historySync.startTaskHistoryRefresh!(
    () => {
      syncCalls.push('sync')
    },
    {
      addWindowListener: (type, listener) => {
        windowListeners.set(type, listener)
      },
      removeWindowListener: type => {
        windowListeners.delete(type)
      },
      addDocumentListener: (type, listener) => {
        documentListeners.set(type, listener)
      },
      removeDocumentListener: type => {
        documentListeners.delete(type)
      },
      setInterval: callback => {
        intervalCallback = callback
        return 7
      },
      clearInterval: id => {
        clearedIntervalId = id
      },
      getVisibilityState: () => visibilityState,
    },
    15000
  )

  assert.equal(typeof intervalCallback, 'function')

  windowListeners.get('focus')?.()
  assert.deepEqual(syncCalls, ['sync'])

  intervalCallback?.()
  assert.deepEqual(syncCalls, ['sync', 'sync'])

  visibilityState = 'hidden'
  intervalCallback?.()
  assert.deepEqual(syncCalls, ['sync', 'sync'])

  documentListeners.get('visibilitychange')?.()
  assert.deepEqual(syncCalls, ['sync', 'sync'])

  visibilityState = 'visible'
  documentListeners.get('visibilitychange')?.()
  assert.deepEqual(syncCalls, ['sync', 'sync', 'sync'])

  stopSync?.()
  assert.equal(clearedIntervalId, 7)
  assert.equal(windowListeners.size, 0)
  assert.equal(documentListeners.size, 0)
})
