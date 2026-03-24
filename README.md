<div style="display: flex; justify-content: center; align-items: center; gap: 10px;">
  <p align="center">
    <img src="./doc/icon.svg" alt="BiliNote Banner" width="50" height="50" />
  </p>
  <h1 align="center">BiliNote</h1>
</div>

<p align="center"><i>AI 视频笔记生成工具，让 AI 为你的视频做笔记</i></p>

## 项目简介

BiliNote 是一个开源的 AI 视频笔记助手，支持通过哔哩哔哩、YouTube、抖音和本地视频自动提取内容并生成结构化 Markdown 笔记。当前版本合并了本地增强和 upstream 新特性，包含：

- 多平台视频笔记生成
- 多版本笔记保留与历史同步
- 移动端首页与设置中心优化
- 笔记顶部视频 Banner
- 基于 RAG 的 AI 问答
- Fast-Whisper / MLX-Whisper / 在线转写配置
- CLI 直接生成笔记
- Docker 与桌面端构建支持

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/JefferyHcool/BiliNote.git
cd BiliNote
cp .env.example .env
```

### 2. 准备依赖

后端使用 `uv`，前端使用 `npm`。

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 后端依赖
uv sync --project backend

# 前端依赖
cd BillNote_frontend
npm ci
cd ..
```

### 3. 启动开发环境

后端：

```bash
cd backend
uv run python main.py
```

前端：

```bash
cd BillNote_frontend
npm run dev
```

默认访问地址：`http://localhost:3015`

### 4. 使用统一脚本管理本地服务

```bash
./scripts/dev.sh start
./scripts/dev.sh status
./scripts/dev.sh logs backend
./scripts/dev.sh restart
./scripts/dev.sh stop
```

### 5. 直接用 CLI 生成笔记

```bash
cd backend
uv run bilinote-cli "https://www.bilibili.com/video/BV19CwVz7EAU"
```

也支持多 URL 并发：

```bash
uv run bilinote-cli "https://www.bilibili.com/video/BV19CwVz7EAU" "https://www.bilibili.com/video/BV11UwDzzEMN" --jobs 2
```

## Docker 部署

标准部署：

```bash
docker-compose up -d
```

GPU 部署：

```bash
docker-compose -f docker-compose.gpu.yml up -d
```

## 配置说明

- `.env.example`：整体项目运行配置
- `backend/.env.example`：后端单独启动时的参考配置
- 模型供应商建议通过前端设置页配置
- B 站场景建议提供 cookies，提高字幕抓取成功率

## 桌面端构建

```bash
chmod +x backend/build.sh
./backend/build.sh
cd BillNote_frontend
npx tauri build
```

## 说明

- 后端依赖以 `backend/pyproject.toml` 为准
- `backend/requirements.txt` 保留给兼容脚本与传统部署方式
- 桌面版构建流程已同步到 GitHub Actions

## License

MIT License
