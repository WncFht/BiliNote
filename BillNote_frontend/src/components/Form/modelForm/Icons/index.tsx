import { getProviderBadge } from '@/lib/providerLogo.ts'
import { cn } from '@/lib/utils.ts'

interface AILogoProps {
  name: string // 图标名称（区分大小写！如 OpenAI、DeepSeek）
  size?: number
}

const toneClassNames = {
  amber: 'bg-amber-100 text-amber-700',
  emerald: 'bg-emerald-100 text-emerald-700',
  orange: 'bg-orange-100 text-orange-700',
  sky: 'bg-sky-100 text-sky-700',
  slate: 'bg-slate-200 text-slate-700',
  violet: 'bg-violet-100 text-violet-700',
} as const

const AILogo = ({ name, size = 24 }: AILogoProps) => {
  const badge = getProviderBadge(name)

  return (
    <span
      aria-label={name || 'AI'}
      className={cn(
        'inline-flex items-center justify-center rounded-xl text-[10px] font-semibold tracking-[0.08em]',
        toneClassNames[badge.tone]
      )}
      style={{ width: size, height: size }}
    >
      {badge.label}
    </span>
  )
}

export default AILogo
