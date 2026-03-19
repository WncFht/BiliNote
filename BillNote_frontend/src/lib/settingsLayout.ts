import { MOBILE_HOME_BREAKPOINT } from './homeLayout.ts'

export interface SettingsHubCard {
  id: 'model' | 'download'
  title: string
  summary: string
  detail: string
  path: string
}

interface SettingsHubCardInput {
  providerCount: number
  enabledProviderCount: number
  enabledModelCount: number
  downloadPlatformCount: number
}

export function getSettingsIndexTarget(width: number): string | null {
  return width >= MOBILE_HOME_BREAKPOINT ? '/settings/model' : null
}

export function getSettingsPageMeta(pathname: string) {
  if (pathname.startsWith('/settings/model')) {
    return {
      title: '模型设置',
      description: '查看供应商与已启用模型',
      backToHub: true,
    }
  }

  if (pathname.startsWith('/settings/download')) {
    return {
      title: '下载配置',
      description: '查看支持平台与 Cookie 设置',
      backToHub: true,
    }
  }

  return {
    title: '设置中心',
    description: '浏览配置摘要与说明',
    backToHub: false,
  }
}

export function buildSettingsHubCards({
  providerCount,
  enabledProviderCount,
  enabledModelCount,
  downloadPlatformCount,
}: SettingsHubCardInput): SettingsHubCard[] {
  return [
    {
      id: 'model',
      title: '模型设置',
      summary:
        enabledModelCount > 0 ? `已启用 ${enabledModelCount} 个模型` : '尚未启用模型，先浏览供应商配置',
      detail:
        providerCount > 0
          ? `${providerCount} 个供应商，其中 ${enabledProviderCount} 个已启用`
          : '当前还没有模型供应商',
      path: '/settings/model',
    },
    {
      id: 'download',
      title: '下载配置',
      summary:
        downloadPlatformCount > 0
          ? `支持平台 ${downloadPlatformCount} 个，按平台管理 Cookie`
          : '支持平台将在这里显示',
      detail: '进入后查看每个平台的下载器配置与编辑入口',
      path: '/settings/download',
    },
  ]
}
