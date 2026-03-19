import { BotMessageSquare, ChevronRight, HardDriveDownload, Info } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/badge.tsx'
import { ScrollArea } from '@/components/ui/scroll-area.tsx'
import { buildSettingsHubCards } from '@/lib/settingsLayout.ts'
import { useModelStore } from '@/store/modelStore'
import { useProviderStore } from '@/store/providerStore'
import { cn } from '@/lib/utils.ts'

const cardIcons = {
  model: BotMessageSquare,
  download: HardDriveDownload,
  about: Info,
} as const

const cardAccents = {
  model: 'from-sky-100 via-white to-blue-50 text-sky-700',
  download: 'from-emerald-100 via-white to-green-50 text-emerald-700',
  about: 'from-amber-100 via-white to-orange-50 text-amber-700',
} as const

const SettingsHub = () => {
  const providers = useProviderStore(state => state.provider)
  const enabledModels = useModelStore(state => state.modelList)

  const cards = buildSettingsHubCards({
    providerCount: providers.length,
    enabledProviderCount: providers.filter(provider => !!provider.enabled).length,
    enabledModelCount: enabledModels.length,
    downloadPlatformCount: 4,
  })

  return (
    <ScrollArea className="h-full bg-transparent">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-5 sm:px-6 sm:py-6">
        <section className="rounded-[28px] border border-white/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(240,249,255,0.86))] p-5 shadow-sm">
          <Badge variant="secondary" className="bg-white/80 text-neutral-700">
            Mobile Settings
          </Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-900">
            先看摘要，再决定要不要改配置
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            手机上的设置页现在优先展示当前状态和说明信息。需要调整时，再进入对应详情页继续编辑。
          </p>
        </section>

        <section className="grid gap-4">
          {cards.map(card => {
            const Icon = cardIcons[card.id]
            return (
              <Link key={card.id} to={card.path} className="group">
                <article className="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-start justify-between gap-4">
                    <div
                      className={cn(
                        'flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br shadow-inner',
                        cardAccents[card.id],
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <ChevronRight className="mt-1 h-5 w-5 text-neutral-300 transition-transform group-hover:translate-x-1 group-hover:text-neutral-500" />
                  </div>

                  <div className="mt-4">
                    <h2 className="text-lg font-semibold text-neutral-900">{card.title}</h2>
                    <p className="mt-2 text-sm font-medium text-neutral-700">{card.summary}</p>
                    <p className="mt-2 text-sm leading-6 text-neutral-500">{card.detail}</p>
                  </div>
                </article>
              </Link>
            )
          })}
        </section>
      </div>
    </ScrollArea>
  )
}

export default SettingsHub
