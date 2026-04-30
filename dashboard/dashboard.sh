#!/usr/bin/env bash
# LibreChat Dashboard — start / stop / restart
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin/python"
APP="$DIR/app.py"
PID_FILE="$DIR/.dashboard.pid"
LOG_FILE="$DIR/.dashboard.log"
HOST="${DASHBOARD_HOST:-0.0.0.0}"
PORT="${DASHBOARD_PORT:-8088}"

_red()   { printf '\033[31m%s\033[0m\n' "$*"; }
_green() { printf '\033[32m%s\033[0m\n' "$*"; }
_cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }

_running_pid() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(<"$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    return 1
}

do_start() {
    if pid=$(_running_pid); then
        _cyan "Dashboard already running (PID $pid)"
        return 0
    fi
    _cyan "Starting Dashboard on ${HOST}:${PORT} ..."
    cd "$DIR"
    nohup "$VENV" "$APP" > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
        _green "Started (PID $pid) — http://${HOST}:${PORT}"
    else
        _red "Failed to start. Check $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

do_stop() {
    if ! pid=$(_running_pid); then
        _cyan "Dashboard is not running"
        return 0
    fi
    _cyan "Stopping Dashboard (PID $pid) ..."
    kill "$pid" 2>/dev/null || true
    for i in $(seq 1 10); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
        _red "Graceful stop failed, force killing ..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    _green "Stopped"
}

do_restart() {
    do_stop
    sleep 0.5
    do_start
}

do_status() {
    if pid=$(_running_pid); then
        _green "Running (PID $pid)"
    else
        _cyan "Not running"
    fi
}

do_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -f "$LOG_FILE"
    else
        _red "No log file: $LOG_FILE"
    fi
}

usage() {
    cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  start     Start the dashboard
  stop      Stop the dashboard
  restart   Restart the dashboard
  status    Check if the dashboard is running
  logs      Tail the log file
EOF
}

case "${1:-}" in
  start)   do_start   ;;
  stop)    do_stop    ;;
  restart) do_restart ;;
  status)  do_status  ;;
  logs)    do_logs    ;;
  *)       usage; exit 1 ;;
esac
