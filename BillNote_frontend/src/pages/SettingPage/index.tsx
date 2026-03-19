import SettingLayout from '@/layouts/SettingLayout.tsx'
import Menu from '@/pages/SettingPage/Menu'
import { useProviderStore } from '@/store/providerStore'
import { useModelStore } from '@/store/modelStore'
import { useEffect } from 'react'

const SettingPage = () => {
  const fetchProviderList = useProviderStore(state => state.fetchProviderList)
  const loadEnabledModels = useModelStore(state => state.loadEnabledModels)

  useEffect(() => {
    fetchProviderList()
    loadEnabledModels()
  }, [fetchProviderList, loadEnabledModels])

  return (
    <div className="h-full w-full">
      <SettingLayout Menu={<Menu />} />
    </div>
  )
}
export default SettingPage
