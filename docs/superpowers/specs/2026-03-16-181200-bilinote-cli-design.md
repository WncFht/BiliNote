# BiliNote CLI Design

## Goal

在不启动前后端服务的前提下，直接复用后端服务层生成 Bilibili 视频 Markdown 笔记，并把这条能力抽成一个可复用的 Codex skill。

## Scope

- 新增命令行入口：`uv run bilinote-cli <url>`
- 默认复用当前本地配置：
  - provider: `openai`
  - model: `gpt-5.4`
  - style: `detailed`
  - `video_understanding=true`
  - `video_interval=4`
  - `grid_size=3x3`
- 默认生成 Markdown 笔记，不生成思维导图
- 默认开启截图，可用 `--no-screenshot` 关闭
- 暴露 `--style` 参数
- 默认输出到现有 `note_results`，可选额外导出到 `--output`
- 新增 Codex skill，内部直接调用该 CLI

## Non-Goals

- 不新增前端页面
- 不新增 HTTP API
- 不支持批量 URL
- 第一版不暴露 provider/model/video interval/grid size 等更多参数

## Architecture

CLI 会复用后端已经存在的初始化链路：

1. 加载 `backend/.env`
2. 初始化数据库与默认 provider
3. 直接调用 `NoteGenerator.generate(...)`
4. 将返回的 `markdown` 写入目标文件，并在终端打印结果路径

这样可以保持与现有 FastAPI 路线一致，避免重新实现下载、转写、截图、视频理解和总结逻辑。

## CLI Contract

```bash
uv run bilinote-cli "<bilibili_url>"
uv run bilinote-cli "<bilibili_url>" --style concise
uv run bilinote-cli "<bilibili_url>" --no-screenshot
uv run bilinote-cli "<bilibili_url>" --style detailed --output /tmp/note.md
```

## Error Handling

- URL 无效或平台不支持时，CLI 直接返回非零退出码
- 笔记生成失败时，打印明确错误信息并返回非零退出码
- 若 provider 配置缺失，直接提示当前默认依赖 `openai/gpt-5.4`

## Validation

- 单元测试验证 CLI 参数到 `NoteGenerator.generate()` 的映射
- 单元测试验证 `--no-screenshot` 与 `--style` 行为
- 真实链接验证一条 Bilibili URL 能产出 Markdown 文件
- Skill 通过直接调用 CLI 命令完成一次真实执行
