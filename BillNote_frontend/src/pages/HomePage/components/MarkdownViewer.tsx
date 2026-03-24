import { FC, Suspense, lazy, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ArrowRight, ExternalLink, Play } from 'lucide-react'
import { toast } from 'react-hot-toast'
import gfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'

import Error from '@/components/Lottie/error.tsx'
import Idle from '@/components/Lottie/Idle.tsx'
import Loading from '@/components/Lottie/Loading.tsx'
import { Button } from '@/components/ui/button.tsx'
import { ScrollArea } from '@/components/ui/scroll-area.tsx'
import { noteStyles } from '@/constant/note.ts'
import { buildTaskProgressDisplay } from '@/lib/taskProgress.ts'
import { buildTaskVideoLink } from '@/lib/videoLink.ts'
import { MarkdownHeader } from '@/pages/HomePage/components/MarkdownHeader.tsx'
import StepBar from '@/pages/HomePage/components/StepBar.tsx'
import TranscriptViewer from '@/pages/HomePage/components/transcriptViewer.tsx'
import VideoBanner from '@/pages/HomePage/components/VideoBanner.tsx'
import { useTaskStore } from '@/store/taskStore'

import 'github-markdown-css/github-markdown-light.css'
import 'katex/dist/katex.min.css'

const MarkmapEditor = lazy(() => import('@/pages/HomePage/components/MarkmapComponent.tsx'))
const MarkdownCodeBlock = lazy(() => import('@/pages/HomePage/components/MarkdownCodeBlock.tsx'))
const MarkdownImage = lazy(() => import('@/pages/HomePage/components/MarkdownImage.tsx'))
const ChatPanel = lazy(() => import('@/pages/HomePage/components/ChatPanel.tsx'))

interface VersionNote {
  ver_id: string
  content: string
  style: string
  model_name: string
  created_at?: string
}

interface MarkdownViewerProps {
  status: 'idle' | 'loading' | 'success' | 'failed'
}

const steps = [
  { label: '解析链接', key: 'PARSING' },
  { label: '下载音频', key: 'DOWNLOADING' },
  { label: '转写文字', key: 'TRANSCRIBING' },
  { label: '总结内容', key: 'SUMMARIZING' },
  { label: '保存完成', key: 'SUCCESS' },
]

const MarkdownViewer: FC<MarkdownViewerProps> = ({ status }) => {
  const [currentVerId, setCurrentVerId] = useState('')
  const [selectedContent, setSelectedContent] = useState('')
  const [modelName, setModelName] = useState('')
  const [style, setStyle] = useState('')
  const [createTime, setCreateTime] = useState('')
  const [showTranscribe, setShowTranscribe] = useState(false)
  const [showChat, setShowChat] = useState<false | 'half' | 'full'>(false)
  const [viewMode, setViewMode] = useState<'map' | 'preview'>('preview')

  const baseURL = String(import.meta.env.VITE_API_BASE_URL || '')
    .replace('/api', '')
    .replace(/\/$/, '')
  const getCurrentTask = useTaskStore.getState().getCurrentTask
  const currentTask = useTaskStore(state => state.getCurrentTask())
  const retryTask = useTaskStore.getState().retryTask
  const taskStatus = currentTask?.status || 'PENDING'
  const taskMessage = currentTask?.message || ''
  const progressDisplay = buildTaskProgressDisplay(taskStatus, taskMessage)
  const videoLink = currentTask ? buildTaskVideoLink(currentTask) : null
  const markdownVersions: VersionNote[] = Array.isArray(currentTask?.markdown)
    ? currentTask.markdown
    : []
  const isMultiVersion = markdownVersions.length > 0
  const canChat = Boolean(currentTask?.id && (taskStatus === 'SUCCESS' || isMultiVersion))

  useEffect(() => {
    if (!currentTask) return

    if (!isMultiVersion) {
      setCurrentVerId('')
      setModelName(currentTask.formData.model_name)
      setStyle(currentTask.formData.style || '')
      setCreateTime(currentTask.createdAt)
      setSelectedContent(typeof currentTask.markdown === 'string' ? currentTask.markdown : '')
      return
    }

    const latestVersion = [...markdownVersions].sort(
      (left, right) =>
        new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime()
    )[0]

    if (latestVersion) {
      setCurrentVerId(latestVersion.ver_id)
    }
  }, [currentTask, isMultiVersion, markdownVersions])

  useEffect(() => {
    if (!isMultiVersion) {
      return
    }

    const currentVersion = markdownVersions.find(version => version.ver_id === currentVerId)
    if (!currentVersion) {
      return
    }

    setModelName(currentVersion.model_name)
    setStyle(currentVersion.style)
    setCreateTime(currentVersion.created_at || '')
    setSelectedContent(currentVersion.content)
  }, [currentVerId, isMultiVersion, markdownVersions])

  useEffect(() => {
    if (!canChat) {
      setShowChat(false)
    }
  }, [canChat, currentTask?.id])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(selectedContent)
      toast.success('已复制到剪贴板')
    } catch {
      toast.error('复制失败')
    }
  }

  const handleDownload = () => {
    const task = getCurrentTask()
    const name = task?.audioMeta.title || 'note'
    const blob = new Blob([selectedContent], { type: 'text/markdown;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${name}.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const renderLazyFallback = (message: string) => (
    <div className="flex items-center justify-center px-4 py-8 text-sm text-neutral-500">
      {message}
    </div>
  )

  const renderChatPanel = (mode: 'half' | 'full') => {
    if (!currentTask?.id) {
      return null
    }

    return (
      <Suspense fallback={renderLazyFallback('AI 问答面板加载中…')}>
        <ChatPanel taskId={currentTask.id} mode={mode} onModeChange={setShowChat} />
      </Suspense>
    )
  }

  if (status === 'loading') {
    return (
      <div className="flex h-full min-h-0 w-full flex-col items-center justify-center space-y-4 px-4 text-center text-neutral-500">
        <StepBar steps={steps} currentStep={taskStatus} />
        <Loading className="h-5 w-5" />
        <div className="w-full max-w-xl text-center text-sm">
          <p className="text-lg font-bold">{progressDisplay.title}</p>
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900 shadow-sm">
            {progressDisplay.detail}
          </div>
          <p className="mt-3 text-xs text-neutral-500">{progressDisplay.hint}</p>
        </div>
      </div>
    )
  }

  if (status === 'idle') {
    return (
      <div className="flex h-full min-h-0 w-full flex-col items-center justify-center space-y-3 px-4 text-center text-neutral-500">
        <Idle />
        <div className="text-center">
          <p className="text-lg font-bold">输入视频链接并点击“生成笔记”</p>
          <p className="mt-2 text-xs text-neutral-500">支持哔哩哔哩、YouTube 、抖音等视频平台</p>
        </div>
      </div>
    )
  }

  if (status === 'failed' && !isMultiVersion) {
    return (
      <div className="flex h-full min-h-0 w-full flex-col items-center justify-center gap-4 space-y-3 px-4 text-center">
        <Error />
        <div className="text-center">
          <p className="text-lg font-bold text-red-500">笔记生成失败</p>
          <p className="mt-2 mb-2 text-xs text-red-400">{taskMessage || '请检查后台或稍后再试'}</p>

          {currentTask?.id && (
            <Button onClick={() => retryTask(currentTask.id)} size="lg">
              重试
            </Button>
          )}
        </div>
      </div>
    )
  }

  const showBanner = Boolean(currentTask?.audioMeta && selectedContent)

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden">
      <MarkdownHeader
        currentTask={
          currentTask
            ? {
                markdown: isMultiVersion ? markdownVersions : currentTask.markdown,
              }
            : undefined
        }
        isMultiVersion={isMultiVersion}
        currentVerId={currentVerId}
        setCurrentVerId={setCurrentVerId}
        modelName={modelName}
        style={style}
        noteStyles={noteStyles}
        onCopy={handleCopy}
        onDownload={handleDownload}
        createAt={createTime}
        videoLink={videoLink}
        showTranscribe={showTranscribe}
        setShowTranscribe={setShowTranscribe}
        showChat={showChat}
        setShowChat={canChat ? setShowChat : undefined}
        viewMode={viewMode}
        setViewMode={setViewMode}
      />

      {showBanner && (
        <div className="px-2 pt-2">
          <VideoBanner audioMeta={currentTask?.audioMeta} videoUrl={currentTask?.formData.video_url} />
        </div>
      )}

      {showChat === 'full' && canChat ? (
        <div className="min-h-0 flex-1 overflow-hidden">{renderChatPanel('full')}</div>
      ) : viewMode === 'map' ? (
        <div className="flex min-h-0 flex-1 overflow-hidden bg-white">
          <div
            className={
              showChat === 'half' && canChat
                ? 'min-h-0 flex-1 overflow-hidden xl:border-r xl:border-neutral-100'
                : 'min-h-0 flex-1 overflow-hidden'
            }
          >
            <Suspense fallback={renderLazyFallback('思维导图加载中…')}>
              <MarkmapEditor
                value={selectedContent}
                onChange={() => {}}
                height="100%"
                title={currentTask?.audioMeta?.title || '思维导图'}
              />
            </Suspense>
          </div>
          {showChat === 'half' && canChat && (
            <div className="hidden min-h-0 xl:block xl:w-[380px]">{renderChatPanel('half')}</div>
          )}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-white py-2 xl:flex-row">
          <div
            className={
              showChat === 'half' && canChat
                ? 'min-h-0 flex-1 overflow-hidden xl:border-r xl:border-neutral-100'
                : 'min-h-0 flex-1 overflow-hidden'
            }
          >
            {selectedContent && selectedContent !== 'loading' && selectedContent !== 'empty' ? (
              <div className="flex min-h-0 h-full flex-col overflow-hidden xl:flex-row">
                <ScrollArea className="min-h-0 w-full flex-1">
                  <div className="markdown-body w-full px-2">
                    <ReactMarkdown
                      remarkPlugins={[gfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        h1: ({ children, ...props }) => (
                          <h1
                            className="text-primary my-6 scroll-m-20 text-3xl font-extrabold tracking-tight lg:text-4xl"
                            {...props}
                          >
                            {children}
                          </h1>
                        ),
                        h2: ({ children, ...props }) => (
                          <h2
                            className="text-primary mt-10 mb-4 scroll-m-20 border-b pb-2 text-2xl font-semibold tracking-tight first:mt-0"
                            {...props}
                          >
                            {children}
                          </h2>
                        ),
                        h3: ({ children, ...props }) => (
                          <h3
                            className="text-primary mt-8 mb-4 scroll-m-20 text-xl font-semibold tracking-tight"
                            {...props}
                          >
                            {children}
                          </h3>
                        ),
                        h4: ({ children, ...props }) => (
                          <h4
                            className="text-primary mt-6 mb-2 scroll-m-20 text-lg font-semibold tracking-tight"
                            {...props}
                          >
                            {children}
                          </h4>
                        ),
                        p: ({ children, ...props }) => (
                          <p className="leading-7 [&:not(:first-child)]:mt-6" {...props}>
                            {children}
                          </p>
                        ),
                        a: ({ href, children, ...props }) => {
                          const firstChild = Array.isArray(children) ? children[0] : children
                          const isOriginLink =
                            typeof firstChild === 'string' && firstChild.startsWith('原片 @')

                          if (isOriginLink) {
                            const timeMatch = firstChild.match(/原片 @ (\d{2}:\d{2})/)
                            const timeText = timeMatch ? timeMatch[1] : '原片'

                            return (
                              <span className="origin-link my-2 inline-flex">
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                                  {...props}
                                >
                                  <Play className="h-3.5 w-3.5" />
                                  <span>原片（{timeText}）</span>
                                </a>
                              </span>
                            )
                          }

                          return (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:text-primary/80 inline-flex items-center gap-0.5 font-medium underline underline-offset-4"
                              {...props}
                            >
                              {children}
                              {href?.startsWith('http') && (
                                <ExternalLink className="ml-0.5 inline-block h-3 w-3" />
                              )}
                            </a>
                          )
                        },
                        img: ({ ...props }) => {
                          let src = props.src || ''
                          if (src.startsWith('/')) {
                            src = baseURL + src
                          }

                          return (
                            <Suspense fallback={renderLazyFallback('图片查看模块加载中…')}>
                              <MarkdownImage alt={props.alt || ''} src={src} />
                            </Suspense>
                          )
                        },
                        strong: ({ children, ...props }) => (
                          <strong className="text-primary font-bold" {...props}>
                            {children}
                          </strong>
                        ),
                        li: ({ children, ...props }) => {
                          const rawText = String(children)
                          const isFakeHeading = /^(\*\*.+\*\*)$/.test(rawText.trim())

                          if (isFakeHeading) {
                            return <div className="text-primary my-4 text-lg font-bold">{children}</div>
                          }

                          return (
                            <li className="my-1" {...props}>
                              {children}
                            </li>
                          )
                        },
                        ul: ({ children, ...props }) => (
                          <ul className="my-6 ml-6 list-disc [&>li]:mt-2" {...props}>
                            {children}
                          </ul>
                        ),
                        ol: ({ children, ...props }) => (
                          <ol className="my-6 ml-6 list-decimal [&>li]:mt-2" {...props}>
                            {children}
                          </ol>
                        ),
                        blockquote: ({ children, ...props }) => (
                          <blockquote
                            className="border-primary/20 text-muted-foreground mt-6 border-l-4 pl-4 italic"
                            {...props}
                          >
                            {children}
                          </blockquote>
                        ),
                        code: ({ inline, className, children, ...props }) => {
                          const match = /language-(\w+)/.exec(className || '')
                          const codeContent = String(children).replace(/\n$/, '')

                          if (!inline && match) {
                            return (
                              <div className="group bg-muted relative my-6 overflow-hidden rounded-lg border shadow-sm">
                                <div className="bg-muted text-muted-foreground flex items-center justify-between px-4 py-1.5 text-sm font-medium">
                                  <div>{match[1].toUpperCase()}</div>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      navigator.clipboard.writeText(codeContent)
                                      toast.success('代码已复制')
                                    }}
                                    className="bg-background/80 hover:bg-background flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors"
                                  >
                                    复制
                                  </button>
                                </div>
                                <Suspense fallback={renderLazyFallback('代码高亮模块加载中…')}>
                                  <MarkdownCodeBlock codeContent={codeContent} language={match[1]} />
                                </Suspense>
                              </div>
                            )
                          }

                          return (
                            <code
                              className="bg-muted relative rounded px-[0.3rem] py-[0.2rem] font-mono text-sm"
                              {...props}
                            >
                              {children}
                            </code>
                          )
                        },
                        table: ({ children, ...props }) => (
                          <div className="my-6 w-full overflow-y-auto">
                            <table className="w-full border-collapse text-sm" {...props}>
                              {children}
                            </table>
                          </div>
                        ),
                        th: ({ children, ...props }) => (
                          <th
                            className="border-muted-foreground/20 border px-4 py-2 text-left font-medium [&[align=center]]:text-center [&[align=right]]:text-right"
                            {...props}
                          >
                            {children}
                          </th>
                        ),
                        td: ({ children, ...props }) => (
                          <td
                            className="border-muted-foreground/20 border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right"
                            {...props}
                          >
                            {children}
                          </td>
                        ),
                        hr: ({ ...props }) => (
                          <hr className="border-muted-foreground/20 my-8" {...props} />
                        ),
                      }}
                    >
                      {selectedContent}
                    </ReactMarkdown>
                  </div>
                </ScrollArea>

                {showTranscribe && (
                  <div className="mt-2 w-full border-t border-neutral-100 pt-2 xl:mt-0 xl:ml-2 xl:w-2/4 xl:border-l xl:border-t-0 xl:pt-0 xl:pl-2">
                    <TranscriptViewer />
                  </div>
                )}
              </div>
            ) : (
              <div className="flex h-full w-full items-center justify-center px-4">
                <div className="flex max-w-[300px] flex-col items-center text-center">
                  <div className="bg-primary-light mb-4 flex h-16 w-16 items-center justify-center rounded-full">
                    <ArrowRight className="text-primary h-8 w-8" />
                  </div>
                  <p className="mb-2 text-neutral-600">输入视频链接并点击"生成笔记"按钮</p>
                  <p className="text-xs text-neutral-500">支持哔哩哔哩、YouTube等视频网站</p>
                </div>
              </div>
            )}
          </div>

          {showChat === 'half' && canChat && (
            <div className="min-h-[320px] w-full shrink-0 border-t border-neutral-100 xl:min-h-0 xl:w-[380px] xl:border-l xl:border-t-0">
              {renderChatPanel('half')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default MarkdownViewer
