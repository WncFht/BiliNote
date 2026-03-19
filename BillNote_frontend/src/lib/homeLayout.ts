export const MOBILE_HOME_BREAKPOINT = 768

export type HomeLayoutMode = 'mobile' | 'desktop'
export type MobileHomeTab = 'create' | 'tasks' | 'preview'

export function getHomeLayoutMode(width: number): HomeLayoutMode {
  return width < MOBILE_HOME_BREAKPOINT ? 'mobile' : 'desktop'
}

export function getDefaultMobileHomeTab(currentTaskId: string | null | undefined): MobileHomeTab {
  return currentTaskId ? 'preview' : 'create'
}

export function getSyncedMobileHomeTab(
  currentTab: MobileHomeTab,
  previousTaskId: string | null | undefined,
  nextTaskId: string | null | undefined,
): MobileHomeTab {
  if (previousTaskId === nextTaskId) {
    return currentTab
  }

  return nextTaskId ? 'preview' : 'create'
}
