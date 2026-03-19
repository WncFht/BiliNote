import test from 'node:test'
import assert from 'node:assert/strict'

import { getManualChunkName } from '../build/manualChunks.ts'

test('getManualChunkName groups markdown and visualization libraries into stable chunks', () => {
  assert.equal(
    getManualChunkName('/workspace/node_modules/react-markdown/index.js'),
    'markdown-preview'
  )
  assert.equal(
    getManualChunkName('/workspace/node_modules/remark-gfm/index.js'),
    'markdown-preview'
  )
  assert.equal(
    getManualChunkName('/workspace/node_modules/markmap-view/dist/index.js'),
    'markmap'
  )
})

test('getManualChunkName splits settings and animation dependencies away from the app shell', () => {
  assert.equal(
    getManualChunkName('/workspace/node_modules/lottie-react/build/index.js'),
    'lottie'
  )
  assert.equal(getManualChunkName('/workspace/node_modules/@lobehub/icons/index.js'), undefined)
  assert.equal(getManualChunkName('/workspace/node_modules/antd/es/index.js'), undefined)
})

test('getManualChunkName leaves ordinary source files untouched', () => {
  assert.equal(getManualChunkName('/workspace/src/App.tsx'), undefined)
})
