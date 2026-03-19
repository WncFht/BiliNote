const markdownPackages = [
  'react-markdown',
  'remark-',
  'rehype-',
  'katex',
  'github-markdown-css',
]

const markmapPackages = [
  'markmap-',
  '/d3-',
]

const codeHighlighterPackages = [
  'react-syntax-highlighter',
  'prismjs',
  'refractor',
]

const imageZoomPackages = [
  'react-medium-image-zoom',
]

const lottiePackages = [
  'lottie-react',
  'lottie-web',
  '@lottiefiles/dotlottie-react',
]

export function getManualChunkName(id: string): string | undefined {
  const normalizedId = id.replaceAll('\\', '/')

  if (!normalizedId.includes('/node_modules/')) {
    return undefined
  }

  if (markdownPackages.some(packageName => normalizedId.includes(packageName))) {
    return 'markdown-preview'
  }

  if (codeHighlighterPackages.some(packageName => normalizedId.includes(packageName))) {
    return 'code-highlighter'
  }

  if (imageZoomPackages.some(packageName => normalizedId.includes(packageName))) {
    return 'image-zoom'
  }

  if (markmapPackages.some(packageName => normalizedId.includes(packageName))) {
    return 'markmap'
  }

  if (lottiePackages.some(packageName => normalizedId.includes(packageName))) {
    return 'lottie'
  }

  if (
    normalizedId.includes('/node_modules/react/') ||
    normalizedId.includes('/node_modules/react-dom/') ||
    normalizedId.includes('/node_modules/scheduler/')
  ) {
    return 'react-core'
  }

  if (
    normalizedId.includes('react-router') ||
    normalizedId.includes('@remix-run/router') ||
    normalizedId.includes('/node_modules/zustand/') ||
    normalizedId.includes('/node_modules/axios/')
  ) {
    return 'app-shell'
  }

  return undefined
}
