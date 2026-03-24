const ABSOLUTE_URL_PATTERN = /^https?:\/\//i

interface ViteProxyEnv {
  BACKEND_PORT?: string
  VITE_API_BASE_URL?: string
  VITE_PROXY_API_TARGET?: string
}

export function resolveViteApiProxyTarget(env: ViteProxyEnv): string {
  const explicitTarget = String(env.VITE_PROXY_API_TARGET || '').trim()
  if (ABSOLUTE_URL_PATTERN.test(explicitTarget)) {
    return explicitTarget
  }

  const apiBaseUrl = String(env.VITE_API_BASE_URL || '').trim()
  if (ABSOLUTE_URL_PATTERN.test(apiBaseUrl)) {
    return apiBaseUrl
  }

  const backendPort = String(env.BACKEND_PORT || '8483').trim() || '8483'
  return `http://127.0.0.1:${backendPort}`
}
