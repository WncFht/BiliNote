# BiliNote CLI Design

## Goal

在不启动前后端服务的前提下，直接复用后端服务层生成一个或多个 Bilibili 视频 Markdown 笔记，并把这条能力抽成一个可复用的 Codex skill。

## Scope

- 新增命令行入口：`uv run bilinote-cli <url...>`
- 默认复用当前本地配置：
  - provider: `openai`
  - model: `gpt-5.4`
  - style: `detailed`
  - `video_understanding=false`
  - `video_interval=4`
  - `grid_size=[]`
- 默认生成 Markdown 笔记，不生成思维导图
- 默认关闭截图，可用 `--screenshot` 开启
- 暴露 `--style` 和 `--jobs` 参数
- 默认输出到 `/Users/fanghaotian/Desktop/obsidian/视频`，最终文件名由 Markdown H1 决定
- 支持批量 URL 原生并发，不把并发调度复杂度放到上游 skill
- Bilibili 字幕链路固定为“平台字幕 -> 下载音频本地转写”，不再回退到 `opencli`
- 新增 Codex skill，内部直接调用该 CLI

## Non-Goals

- 不新增前端页面
- 不新增 HTTP API
- 第一版不暴露 provider/model/video interval/grid size 等更多参数

## Architecture

CLI 会复用后端已经存在的初始化链路：

1. 加载 `backend/.env`
2. 初始化数据库与默认 provider
3. 直接调用 `NoteGenerator.generate(...)`
4. 单 URL 时直接写入目标文件；多 URL 时通过线程池并发执行多个 `generate(...)`
5. 将返回的 `markdown` 写入目标文件，并在终端打印结果路径

这样可以保持与现有 FastAPI 路线一致，避免重新实现下载、转写、截图、视频理解和总结逻辑。

## CLI Contract

```bash
uv run bilinote-cli "<bilibili_url>"
uv run bilinote-cli "<bilibili_url>" --style concise
uv run bilinote-cli "<bilibili_url>" --screenshot
uv run bilinote-cli "<bilibili_url>" --style detailed --output /Users/fanghaotian/Desktop/obsidian/视频
uv run bilinote-cli "<url1>" "<url2>" --jobs 2 --output /Users/fanghaotian/Desktop/obsidian/视频
```

## Error Handling

- URL 无效或平台不支持时，CLI 直接返回非零退出码
- 笔记生成失败时，打印明确错误信息并返回非零退出码
- 批量模式下若 `--output` 指向单个 `.md` 文件，直接报错
- 若 provider 配置缺失，直接提示当前默认依赖 `openai/gpt-5.4`

## Validation

- 单元测试验证 CLI 参数到 `NoteGenerator.generate()` 的映射
- 单元测试验证 `--screenshot`、`--style`、`--jobs` 与批量输出行为
- 单元测试验证 Bilibili 字幕缺失时不会再触发 `opencli`，而是回到本地转写链路
- 真实链接验证一条 Bilibili URL 能产出 Markdown 文件
- Skill 通过直接调用 CLI 命令完成一次真实执行
