import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Tag } from 'antd'
import { useParams } from 'react-router-dom'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

import { ModelSelector } from '@/components/Form/modelForm/ModelSelector.tsx'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { getProviderTestErrorMessage } from '@/lib/providerErrors.ts'
import { deleteModelById, testConnection } from '@/services/model.ts'
import { useModelStore } from '@/store/modelStore'
import { useProviderStore } from '@/store/providerStore'

const ProviderSchema = z.object({
  name: z.string().min(2, '名称不能少于 2 个字符'),
  apiKey: z.string().optional(),
  baseUrl: z.string().url('必须是合法 URL'),
  type: z.string(),
})

type ProviderFormValues = z.infer<typeof ProviderSchema>

interface EnabledModelRecord {
  id: number
  model_name: string
}

const ProviderForm = ({ isCreate = false }: { isCreate?: boolean }) => {
  let { id } = useParams()
  const isEditMode = !isCreate

  const loadProviderById = useProviderStore(state => state.loadProviderById)
  const updateProvider = useProviderStore(state => state.updateProvider)
  const addNewProvider = useProviderStore(state => state.addNewProvider)
  const loadModelsById = useModelStore(state => state.loadModelsById)

  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [isBuiltIn, setIsBuiltIn] = useState(false)
  const [models, setModels] = useState<EnabledModelRecord[]>([])

  const providerForm = useForm<ProviderFormValues>({
    resolver: zodResolver(ProviderSchema),
    defaultValues: {
      name: '',
      apiKey: '',
      baseUrl: '',
      type: 'custom',
    },
  })

  useEffect(() => {
    const load = async () => {
      if (isEditMode) {
        const data = await loadProviderById(id!)
        providerForm.reset(data)
        setIsBuiltIn(data.type === 'built-in')
      } else {
        providerForm.reset({
          name: '',
          apiKey: '',
          baseUrl: '',
          type: 'custom',
        })
        setIsBuiltIn(false)
      }

      if (id) {
        const providerModels = await loadModelsById(id)
        if (providerModels) {
          setModels(providerModels)
        }
      } else {
        setModels([])
      }

      setLoading(false)
    }

    void load()
  }, [id, isEditMode, loadModelsById, loadProviderById, providerForm])

  const handleDelete = async (modelId: number) => {
    if (!window.confirm('确定要删除这个模型吗？')) return

    try {
      await deleteModelById(modelId)
      toast.success('删除成功')
    } catch {
      toast.error('删除异常')
    }
  }

  const handleTest = async () => {
    const values = providerForm.getValues()
    if (!values.apiKey || !values.baseUrl) {
      toast.error('请填写 API Key 和 Base URL')
      return
    }

    if (!id) {
      toast.error('请先保存供应商信息')
      return
    }

    try {
      setTesting(true)
      await testConnection({ id })
      toast.success('测试连通性成功 🎉')
    } catch (error) {
      toast.error(`连接失败: ${getProviderTestErrorMessage(error)}`)
    } finally {
      setTesting(false)
    }
  }

  const onProviderSubmit = async (values: ProviderFormValues) => {
    if (isEditMode) {
      await updateProvider({ ...values, id: id! })
      toast.success('更新供应商成功')
      return
    }

    id = await addNewProvider({ ...values })
    toast.success('新增供应商成功')
  }

  if (loading) return <div className="p-4">加载中...</div>

  return (
    <div className="flex flex-col gap-8 p-4">
      <Form {...providerForm}>
        <form
          onSubmit={providerForm.handleSubmit(onProviderSubmit)}
          className="flex max-w-xl flex-col gap-4"
        >
          <div className="text-lg font-bold">{isEditMode ? '编辑模型供应商' : '新增模型供应商'}</div>
          {!isBuiltIn && (
            <div className="text-sm text-red-500 italic">自定义模型供应商需要确保兼容 OpenAI SDK</div>
          )}

          <FormField
            control={providerForm.control}
            name="name"
            render={({ field }) => (
              <FormItem className="flex items-center gap-4">
                <FormLabel className="w-24 text-right">名称</FormLabel>
                <FormControl>
                  <Input {...field} disabled={isBuiltIn} className="flex-1" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={providerForm.control}
            name="apiKey"
            render={({ field }) => (
              <FormItem className="flex items-center gap-4">
                <FormLabel className="w-24 text-right">API Key</FormLabel>
                <FormControl>
                  <Input {...field} className="flex-1" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={providerForm.control}
            name="baseUrl"
            render={({ field }) => (
              <FormItem className="flex items-center gap-4">
                <FormLabel className="w-24 text-right">API地址</FormLabel>
                <FormControl>
                  <Input {...field} className="flex-1" />
                </FormControl>
                <Button type="button" onClick={handleTest} variant="ghost" disabled={testing}>
                  {testing ? '测试中...' : '测试连通性'}
                </Button>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={providerForm.control}
            name="type"
            render={({ field }) => (
              <FormItem className="flex items-center gap-4">
                <FormLabel className="w-24 text-right">类型</FormLabel>
                <FormControl>
                  <Input {...field} disabled className="flex-1" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="pt-2">
            <Button type="submit" disabled={!providerForm.formState.isDirty}>
              {isEditMode ? '保存修改' : '保存创建'}
            </Button>
          </div>
        </form>
      </Form>

      <div className="flex max-w-xl flex-col gap-4">
        <div className="flex flex-col gap-2">
          <span className="font-bold">模型列表</span>
          <div className="flex flex-col gap-2 rounded bg-[#FEF0F0] p-2.5">
            <h2 className="font-bold">注意!</h2>
            <span>请确保已经保存供应商信息,以及通过测试连通性.</span>
          </div>
          {id ? (
            <ModelSelector providerId={id} />
          ) : (
            <div className="rounded border border-dashed p-4 text-sm text-neutral-500">
              保存供应商后即可加载并启用模型。
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <span className="font-bold">已启用模型</span>
          <div className="flex flex-wrap gap-2 rounded p-2.5">
            {models.map(model => (
              <Tag
                key={model.id}
                closable
                color="blue"
                onClose={() => {
                  void handleDelete(model.id)
                }}
              >
                {model.model_name}
              </Tag>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProviderForm
