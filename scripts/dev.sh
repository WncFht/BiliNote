#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NO_PROXY_VALUE="${NO_PROXY_VALUE:-127.0.0.1,localhost,::1}"
TAIL_LINES="${TAIL_LINES:-40}"

BACKEND_WORKDIR="${BILINOTE_BACKEND_WORKDIR:-$ROOT_DIR/backend}"
FRONTEND_WORKDIR="${BILINOTE_FRONTEND_WORKDIR:-$ROOT_DIR/BillNote_frontend}"

BACKEND_PID_FILE="${BILINOTE_BACKEND_PID_FILE:-$ROOT_DIR/backend.local.pid}"
FRONTEND_PID_FILE="${BILINOTE_FRONTEND_PID_FILE:-$ROOT_DIR/frontend.local.pid}"

BACKEND_LOG_FILE="${BILINOTE_BACKEND_LOG_FILE:-$ROOT_DIR/backend.local.log}"
FRONTEND_LOG_FILE="${BILINOTE_FRONTEND_LOG_FILE:-$ROOT_DIR/frontend.local.log}"

BACKEND_CMD="${BILINOTE_BACKEND_CMD:-uv run python main.py}"
FRONTEND_CMD="${BILINOTE_FRONTEND_CMD:-pnpm dev}"
FRONTEND_PREVIEW_PORT="${BILINOTE_FRONTEND_PREVIEW_PORT:-3015}"
FRONTEND_PREVIEW_CMD="${BILINOTE_FRONTEND_PREVIEW_CMD:-pnpm build && pnpm exec vite preview --host 0.0.0.0 --port $FRONTEND_PREVIEW_PORT}"

usage() {
  cat <<EOF
Usage: ./scripts/dev.sh <command> [service]

Commands:
  start              Start backend and frontend
  start-preview      Start backend and frontend preview build
  stop               Stop backend and frontend
  restart            Restart backend and frontend
  restart-preview    Restart backend and frontend preview build
  status             Show service status
  logs [service]     Show recent logs for backend, frontend, or all
  help               Show this help
EOF
}

ensure_parent_dir() {
  mkdir -p "$(dirname "$1")"
}

pid_is_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local pid_file="$1"
  tr -d '[:space:]' < "$pid_file"
}

service_running() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi

  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 1
  fi

  if pid_is_alive "$pid"; then
    return 0
  fi

  rm -f "$pid_file"
  return 1
}

start_service() {
  local name="$1"
  local workdir="$2"
  local pid_file="$3"
  local log_file="$4"
  local command="$5"

  ensure_parent_dir "$pid_file"
  ensure_parent_dir "$log_file"

  if service_running "$pid_file"; then
    echo "$name: already running (pid $(read_pid "$pid_file"))"
    return 0
  fi

  (
    cd "$workdir"
    nohup env \
      -u HTTP_PROXY \
      -u HTTPS_PROXY \
      -u http_proxy \
      -u https_proxy \
      -u ALL_PROXY \
      -u all_proxy \
      NO_PROXY="$NO_PROXY_VALUE" \
      no_proxy="$NO_PROXY_VALUE" \
      bash -lc "$command" >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
  )

  sleep 1

  if service_running "$pid_file"; then
    echo "$name: started (pid $(read_pid "$pid_file"))"
    return 0
  fi

  echo "$name: failed to start" >&2
  tail -n "$TAIL_LINES" "$log_file" 2>/dev/null || true
  return 1
}

stop_service() {
  local name="$1"
  local pid_file="$2"

  if ! service_running "$pid_file"; then
    rm -f "$pid_file"
    echo "$name: already stopped"
    return 0
  fi

  local pid
  pid="$(read_pid "$pid_file")"
  kill "$pid" 2>/dev/null || true

  local _i
  for _i in {1..20}; do
    if ! pid_is_alive "$pid"; then
      rm -f "$pid_file"
      echo "$name: stopped"
      return 0
    fi
    sleep 0.25
  done

  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  echo "$name: stopped (forced)"
}

print_status() {
  if service_running "$BACKEND_PID_FILE"; then
    echo "backend: running (pid $(read_pid "$BACKEND_PID_FILE"))"
  else
    echo "backend: stopped"
  fi

  if service_running "$FRONTEND_PID_FILE"; then
    echo "frontend: running (pid $(read_pid "$FRONTEND_PID_FILE"))"
  else
    echo "frontend: stopped"
  fi
}

show_logs() {
  local target="${1:-all}"

  case "$target" in
    backend)
      tail -n "$TAIL_LINES" "$BACKEND_LOG_FILE"
      ;;
    frontend)
      tail -n "$TAIL_LINES" "$FRONTEND_LOG_FILE"
      ;;
    all)
      echo "== backend =="
      tail -n "$TAIL_LINES" "$BACKEND_LOG_FILE" 2>/dev/null || true
      echo
      echo "== frontend =="
      tail -n "$TAIL_LINES" "$FRONTEND_LOG_FILE" 2>/dev/null || true
      ;;
    *)
      echo "Unknown service: $target" >&2
      exit 1
      ;;
  esac
}

start_all() {
  start_service "backend" "$BACKEND_WORKDIR" "$BACKEND_PID_FILE" "$BACKEND_LOG_FILE" "$BACKEND_CMD"
  start_service "frontend" "$FRONTEND_WORKDIR" "$FRONTEND_PID_FILE" "$FRONTEND_LOG_FILE" "$FRONTEND_CMD"
}

start_preview_all() {
  start_service "backend" "$BACKEND_WORKDIR" "$BACKEND_PID_FILE" "$BACKEND_LOG_FILE" "$BACKEND_CMD"
  start_service "frontend" "$FRONTEND_WORKDIR" "$FRONTEND_PID_FILE" "$FRONTEND_LOG_FILE" "$FRONTEND_PREVIEW_CMD"
}

stop_all() {
  stop_service "frontend" "$FRONTEND_PID_FILE"
  stop_service "backend" "$BACKEND_PID_FILE"
}

COMMAND="${1:-status}"

case "$COMMAND" in
  start)
    start_all
    ;;
  start-preview)
    start_preview_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_all
    ;;
  restart-preview)
    stop_all
    start_preview_all
    ;;
  status)
    print_status
    ;;
  logs)
    show_logs "${2:-all}"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
