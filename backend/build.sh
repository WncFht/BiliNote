#!/usr/bin/env bash
set -e
# uncomment this for debugging
# set -x

cd "$(dirname "$0")/.."

echo "当前工作目录：$(pwd)"

echo "清理旧的构建..."
rm -rf backend/dist backend/build ./BillNote_frontend/src-tauri/bin/*
echo "清理完成。"

TARGET_TRIPLE=$(rustc -Vv | grep host | cut -f2 -d' ')
echo "Detected target triple: $TARGET_TRIPLE"

echo "为打包准备 .env 文件..."
cp .env.example backend/.env

echo "开始 PyInstaller 打包..."
uv --project backend run pyinstaller \
  -y \
  --name BiliNoteBackend \
  --paths backend \
  --distpath ./BillNote_frontend/src-tauri/bin \
  --workpath backend/build \
  --specpath backend \
  --hidden-import uvicorn \
  --hidden-import fastapi \
  --hidden-import starlette \
  --add-data "app/db/builtin_providers.json:." \
  --add-data ".env:." \
  "$(pwd)/backend/main.py"

echo "清理临时的 .env 文件..."
rm backend/.env

mv \
 ./BillNote_frontend/src-tauri/bin/BiliNoteBackend/BiliNoteBackend \
 ./BillNote_frontend/src-tauri/bin/BiliNoteBackend/BiliNoteBackend-$TARGET_TRIPLE

echo "PyInstaller 打包完成。"
echo "打包后的目录内容："
ls -l ./BillNote_frontend/src-tauri/bin/BiliNoteBackend

echo "请检查 src-tauri/bin/BiliNoteBackend 目录，确认其中包含了名为 .env 的【文件】。"
