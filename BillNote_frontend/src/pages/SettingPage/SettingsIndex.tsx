import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { getSettingsIndexTarget } from '@/lib/settingsLayout.ts'
import SettingsHub from '@/pages/SettingPage/SettingsHub.tsx'

const getInitialTarget = () => {
  if (typeof window === 'undefined') {
    return '/settings/model'
  }

  return getSettingsIndexTarget(window.innerWidth)
}

const SettingsIndex = () => {
  const [redirectTarget, setRedirectTarget] = useState<string | null>(getInitialTarget)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    const syncTarget = () => {
      setRedirectTarget(getSettingsIndexTarget(window.innerWidth))
    }

    syncTarget()
    window.addEventListener('resize', syncTarget)

    return () => window.removeEventListener('resize', syncTarget)
  }, [])

  if (redirectTarget) {
    return <Navigate to={redirectTarget} replace />
  }

  return <SettingsHub />
}

export default SettingsIndex
