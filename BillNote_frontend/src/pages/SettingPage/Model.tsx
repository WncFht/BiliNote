import Provider from '@/components/Form/modelForm/Provider.tsx'
import { Outlet, useLocation } from 'react-router-dom'
import { Badge } from '@/components/ui/badge.tsx'
import { useModelStore } from '@/store/modelStore'
import { useProviderStore } from '@/store/providerStore'

const Model = () => {
  const location = useLocation()
  const providers = useProviderStore(state => state.provider)
  const enabledModels = useModelStore(state => state.modelList)
  const showDetail = location.pathname !== '/settings/model'

  return (
    <div className="flex h-full min-h-0 flex-col bg-white md:flex-row">
      <div className="border-b border-neutral-200 p-3 md:hidden">
        <div className="rounded-3xl border border-sky-100 bg-[linear-gradient(135deg,rgba(240,249,255,0.95),rgba(255,255,255,0.95))] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="bg-white text-sky-700">
              模型概览
            </Badge>
            <Badge variant="secondary" className="bg-white text-neutral-700">
              {enabledModels.length} 个已启用
            </Badge>
          </div>
          <p className="mt-3 text-sm font-medium text-neutral-800">
            {providers.length > 0
              ? `当前共有 ${providers.length} 个供应商，可继续查看详情或新增供应商。`
              : '还没有模型供应商，先创建一个入口最清晰。'}
          </p>
          <p className="mt-2 text-xs leading-5 text-neutral-500">
            手机端会优先展示摘要和列表，需要编辑时再进入具体表单。
          </p>
        </div>
      </div>

      <div className="min-h-0 w-full border-b border-neutral-200 p-3 md:w-[320px] md:shrink-0 md:border-b-0 md:border-r">
        <Provider />
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {showDetail ? (
          <Outlet />
        ) : (
          <div className="flex h-full items-center justify-center px-6 py-8">
            <div className="max-w-md rounded-[28px] border border-neutral-200 bg-white p-6 text-center shadow-sm">
              <h2 className="text-xl font-semibold text-neutral-900">先浏览，再进入编辑</h2>
              <p className="mt-3 text-sm leading-6 text-neutral-500">
                从供应商列表里点开已有项，或新增一个模型供应商。手机端默认不直接铺满重表单。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
export default Model
