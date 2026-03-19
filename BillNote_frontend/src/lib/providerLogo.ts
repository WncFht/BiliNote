const PROVIDER_BADGES: Record<string, { label: string; tone: ProviderBadgeTone }> = {
  openai: { label: 'OA', tone: 'emerald' },
  deepseek: { label: 'DS', tone: 'sky' },
  claude: { label: 'CL', tone: 'amber' },
  gemini: { label: 'GM', tone: 'violet' },
  qwen: { label: 'QW', tone: 'orange' },
  custom: { label: 'AI', tone: 'slate' },
}

export type ProviderBadgeTone = 'amber' | 'emerald' | 'orange' | 'sky' | 'slate' | 'violet'

export interface ProviderBadge {
  label: string
  tone: ProviderBadgeTone
}

export function getProviderBadge(name: string): ProviderBadge {
  const normalizedName = name.trim().toLowerCase()

  if (normalizedName in PROVIDER_BADGES) {
    return PROVIDER_BADGES[normalizedName]
  }

  const alphanumeric = normalizedName.replace(/[^a-z0-9]+/g, '')
  const label = alphanumeric.slice(0, 2).toUpperCase() || 'AI'

  return {
    label,
    tone: 'slate',
  }
}
