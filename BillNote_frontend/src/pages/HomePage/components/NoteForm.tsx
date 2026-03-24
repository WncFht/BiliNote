import { zodResolver } from '@hookform/resolvers/zod'
import { Info, Loader2, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { type FieldErrors, useForm, useWatch } from 'react-hook-form'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { Button } from '@/components/ui/button.tsx'
import { Checkbox } from '@/components/ui/checkbox.tsx'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form.tsx'
import { Input } from '@/components/ui/input.tsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.tsx'
import { Textarea } from '@/components/ui/textarea.tsx'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip.tsx'
import { noteStyles, videoPlatforms } from '@/constant/note.ts'
import {
  buildDefaultWebNoteFormValues,
  normalizeWebGenerateNotePayload,
  WEB_NOTE_FORMATS,
} from '@/lib/noteRequest.ts'
import { resolveProviderIdForModel } from '@/lib/noteSubmission.ts'
import { cn } from '@/lib/utils.ts'
import { generateNote } from '@/services/note.ts'
import { uploadFile } from '@/services/upload.ts'
import { useModelStore } from '@/store/modelStore'
import { useTaskStore } from '@/store/taskStore'

const formSchema = z
  .object({
    video_url: z.string().optional(),
    platform: z.string().nonempty('请选择平台'),
    quality: z.enum(['fast', 'medium', 'slow']),
    screenshot: z.boolean().optional(),
    link: z.boolean().optional(),
    model_name: z.string().nonempty('请选择模型'),
    format: z.array(z.string()).default([]),
    style: z.string().nonempty('请选择笔记生成风格'),
    extras: z.string().optional(),
    video_understanding: z.boolean().optional(),
    video_interval: z.coerce.number().min(1).max(30).default(4).optional(),
    grid_size: z
      .union([
        z.tuple([z.coerce.number().min(1).max(10), z.coerce.number().min(1).max(10)]),
        z.tuple([]),
      ])
      .default([])
      .optional(),
  })
  .superRefine(({ video_url, platform }, ctx) => {
    if (platform === 'local') {
      if (!video_url) {
        ctx.addIssue({ code: 'custom', message: '本地视频路径不能为空', path: ['video_url'] })
      }
      return
    }

    if (!video_url) {
      ctx.addIssue({ code: 'custom', message: '视频链接不能为空', path: ['video_url'] })
      return
    }

    try {
      const url = new URL(video_url)
      if (!['http:', 'https:'].includes(url.protocol)) {
        throw new Error()
      }
    } catch {
      ctx.addIssue({ code: 'custom', message: '请输入正确的视频链接', path: ['video_url'] })
    }
  })

export type NoteFormValues = z.infer<typeof formSchema>

const SectionHeader = ({ title, tip }: { title: string; tip?: string }) => (
  <div className="my-3 flex items-center justify-between">
    <h2 className="block">{title}</h2>
    {tip && (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Info className="hover:text-primary h-4 w-4 cursor-pointer text-neutral-400" />
          </TooltipTrigger>
          <TooltipContent className="text-xs">{tip}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )}
  </div>
)

const CheckboxGroup = ({
  value = [],
  onChange,
  disabledMap,
}: {
  value?: string[]
  onChange: (value: string[]) => void
  disabledMap: Record<string, boolean>
}) => (
  <div className="flex flex-wrap gap-x-4 gap-y-2">
    {WEB_NOTE_FORMATS.map(({ label, value: itemValue }) => (
      <label key={itemValue} className="flex items-center space-x-2">
        <Checkbox
          checked={value.includes(itemValue)}
          disabled={disabledMap[itemValue]}
          onCheckedChange={checked =>
            onChange(checked ? [...value, itemValue] : value.filter(item => item !== itemValue))
          }
        />
        <span>{label}</span>
      </label>
    ))}
  </div>
)

const NoteForm = () => {
  const navigate = useNavigate()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const { addPendingTask, currentTaskId, setCurrentTask, getCurrentTask, retryTask } =
    useTaskStore()
  const { loadEnabledModels, modelList } = useModelStore()

  const form = useForm<NoteFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: buildDefaultWebNoteFormValues(modelList[0]?.model_name || ''),
  })
  const currentTask = getCurrentTask()
  const platform = useWatch({ control: form.control, name: 'platform' }) as string
  const editing = Boolean(currentTask?.id)

  useEffect(() => {
    void loadEnabledModels()
  }, [loadEnabledModels])

  useEffect(() => {
    if (!currentTask) return

    const { formData } = currentTask
    form.reset(
      normalizeWebGenerateNotePayload({
        ...buildDefaultWebNoteFormValues(formData.model_name || modelList[0]?.model_name || ''),
        platform: formData.platform || 'bilibili',
        video_url: formData.video_url || '',
        model_name: formData.model_name || modelList[0]?.model_name || '',
        style: formData.style || 'detailed',
        quality: formData.quality || 'medium',
        extras: formData.extras || '',
        link: formData.link ?? false,
        format: formData.format,
      })
    )
  }, [currentTask, currentTaskId, form, modelList])

  const generating = !['SUCCESS', 'FAILED', undefined].includes(getCurrentTask()?.status)

  const handleFileUpload = async (file: File, onUploaded: (url: string) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    setIsUploading(true)
    setUploadSuccess(false)

    try {
      const data = await uploadFile(formData)
      onUploaded(data.url)
      setUploadSuccess(true)
    } catch (error) {
      console.error('上传失败:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const onSubmit = async (values: NoteFormValues) => {
    let providerId: string
    try {
      providerId = resolveProviderIdForModel(modelList, values.model_name)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '当前模型不可用，请刷新模型列表后重试')
      return
    }

    const payload = normalizeWebGenerateNotePayload({
      ...values,
      provider_id: providerId,
      task_id: currentTaskId || '',
    })

    if (currentTaskId) {
      void retryTask(currentTaskId, payload)
      return
    }

    const data = await generateNote(payload)
    if (!data) {
      return
    }

    addPendingTask(data.task_id, values.platform, payload)
  }

  const onInvalid = (errors: FieldErrors<NoteFormValues>) => {
    console.warn('表单校验失败：', errors)
  }

  const handleCreateNew = () => {
    setCurrentTask(null)
  }

  return (
    <div className="h-full w-full" data-mobile-form>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit, onInvalid)} className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="submit"
              className={cn('w-full bg-primary', editing && 'sm:w-2/3')}
              disabled={generating}
            >
              {generating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {generating ? '正在生成…' : editing ? '重新生成' : '生成笔记'}
            </Button>

            {editing && (
              <Button
                type="button"
                variant="outline"
                className="w-full sm:w-1/3"
                onClick={handleCreateNew}
              >
                <Plus className="mr-2 h-4 w-4" />
                新建笔记
              </Button>
            )}
          </div>

          <SectionHeader title="视频链接" tip="支持 B 站、YouTube 等平台" />
          <div className="flex flex-col gap-2 sm:flex-row">
            <FormField
              control={form.control}
              name="platform"
              render={({ field }) => (
                <FormItem>
                  <Select
                    disabled={editing}
                    value={field.value}
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-32">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {videoPlatforms.map(platformOption => (
                        <SelectItem key={platformOption.value} value={platformOption.value}>
                          <div className="flex items-center justify-center gap-2">
                            <div className="h-4 w-4">{platformOption.logo()}</div>
                            <span>{platformOption.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage style={{ display: 'none' }} />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="video_url"
              render={({ field }) => (
                <FormItem className="flex-1">
                  {platform === 'local' ? (
                    <Input disabled={editing} placeholder="请输入本地视频路径" {...field} />
                  ) : (
                    <Input disabled={editing} placeholder="请输入视频网站链接" {...field} />
                  )}
                  <FormMessage style={{ display: 'none' }} />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="video_url"
            render={({ field }) => (
              <FormItem className="flex-1">
                {platform === 'local' && (
                  <div
                    className="hover:border-primary mt-2 flex h-40 cursor-pointer items-center justify-center rounded-md border-2 border-dashed border-gray-300 transition-colors"
                    onDragOver={event => {
                      event.preventDefault()
                      event.stopPropagation()
                    }}
                    onDrop={event => {
                      event.preventDefault()
                      const file = event.dataTransfer.files?.[0]
                      if (file) handleFileUpload(file, field.onChange)
                    }}
                    onClick={() => {
                      const input = document.createElement('input')
                      input.type = 'file'
                      input.accept = 'video/*'
                      input.onchange = event => {
                        const file = (event.target as HTMLInputElement).files?.[0]
                        if (file) handleFileUpload(file, field.onChange)
                      }
                      input.click()
                    }}
                  >
                    {isUploading ? (
                      <p className="text-center text-sm text-blue-500">上传中，请稍候…</p>
                    ) : uploadSuccess ? (
                      <p className="text-center text-sm text-green-500">上传成功！</p>
                    ) : (
                      <p className="text-center text-sm text-gray-500">
                        拖拽文件到这里上传 <br />
                        <span className="text-xs text-gray-400">或点击选择文件</span>
                      </p>
                    )}
                  </div>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {modelList.length > 0 ? (
              <FormField
                control={form.control}
                name="model_name"
                render={({ field }) => (
                  <FormItem>
                    <SectionHeader title="模型选择" tip="不同模型效果不同，建议自行测试" />
                    <Select
                      onOpenChange={() => {
                        void loadEnabledModels()
                      }}
                      value={field.value}
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full min-w-0 truncate">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {modelList.map(model => (
                          <SelectItem key={model.id} value={model.model_name}>
                            {model.model_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <FormItem>
                <SectionHeader title="模型选择" tip="不同模型效果不同，建议自行测试" />
                <Button type="button" variant="outline" onClick={() => navigate('/settings/model')}>
                  请先添加模型
                </Button>
                <FormMessage />
              </FormItem>
            )}

            <FormField
              control={form.control}
              name="style"
              render={({ field }) => (
                <FormItem>
                  <SectionHeader title="笔记风格" tip="选择生成笔记的呈现风格" />
                  <Select value={field.value} onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full min-w-0 truncate">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {noteStyles.map(({ label, value }) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="format"
            render={({ field }) => (
              <FormItem>
                <SectionHeader title="笔记格式" tip="选择要包含的笔记元素" />
                <CheckboxGroup
                  value={field.value}
                  onChange={field.onChange}
                  disabledMap={{
                    link: platform === 'local',
                    toc: false,
                    summary: false,
                  }}
                />
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="extras"
            render={({ field }) => (
              <FormItem>
                <SectionHeader title="备注" tip="可在 Prompt 结尾附加自定义说明" />
                <Textarea placeholder="笔记需要罗列出 xxx 关键点…" {...field} />
                <FormMessage />
              </FormItem>
            )}
          />
        </form>
      </Form>
    </div>
  )
}

export default NoteForm
