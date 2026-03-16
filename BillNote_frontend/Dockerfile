# === 前端构建阶段 ===
FROM node:18-bullseye AS builder

# 安装固定版本的 pnpm，减少无锁文件场景下的构建漂移
RUN npm install -g pnpm@9

# 设置工作目录
WORKDIR /app

# 拷贝前端源码
COPY ./BillNote_frontend /app

ENV NODE_OPTIONS=--max-old-space-size=2048

# 如果宿主机已经预构建 dist，就直接复用，避免低内存 Docker 环境重复编译前端
RUN if [ -f dist/index.html ]; then \
      echo "Using prebuilt frontend dist"; \
    else \
      pnpm install && \
      arch="$(dpkg --print-architecture)" && \
      case "$arch" in \
        amd64) oxide_pkg='@tailwindcss/oxide-linux-x64-gnu@4.2.1' ;; \
        arm64) oxide_pkg='@tailwindcss/oxide-linux-arm64-gnu@4.2.1' ;; \
        *) echo "Unsupported build arch: $arch" >&2; exit 1 ;; \
      esac && \
      pnpm add -D "$oxide_pkg" && \
      pnpm run build; \
    fi

# --- 阶段2：使用 nginx 作为静态服务器 ---
FROM nginx:1.25-alpine

# 删除默认配置（可选）
RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./BillNote_frontend/deploy/default.conf /etc/nginx/conf.d/default.conf


# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html
