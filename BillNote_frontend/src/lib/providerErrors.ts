type ErrorShape = {
  msg?: unknown
  message?: unknown
  data?: {
    msg?: unknown
  }
  response?: {
    data?: {
      msg?: unknown
    }
  }
}

function getStringCandidate(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

export function getProviderTestErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    const typedError = error as ErrorShape

    return (
      getStringCandidate(typedError.msg)
      ?? getStringCandidate(typedError.data?.msg)
      ?? getStringCandidate(typedError.response?.data?.msg)
      ?? getStringCandidate(typedError.message)
      ?? '未知错误'
    )
  }

  return getStringCandidate(error) ?? '未知错误'
}
