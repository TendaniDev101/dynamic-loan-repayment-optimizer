#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
FRONTEND_DIR="$ROOT_DIR/frontend"
NODE_VERSION_FILE="$ROOT_DIR/.nvmrc"
NODE_VERSION="${NODE_VERSION:-$(<"$NODE_VERSION_FILE")}"
NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
BACKEND_PID=""

log() {
  printf '[loan-optimizer] %s\n' "$1"
}

ensure_node_version() {
  if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
    log "nvm was not found at $NVM_DIR/nvm.sh."
    log "Install nvm and Node $NODE_VERSION, or run with NVM_DIR pointing to your nvm install."
    exit 1
  fi

  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"

  if ! nvm use "$NODE_VERSION" >/dev/null 2>&1; then
    log "Node $NODE_VERSION is not installed in nvm."
    log "Run 'nvm install $NODE_VERSION' once, then rerun this script."
    exit 1
  fi

  log "Using Node $(node --version) via nvm."
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    log "Stopping backend process ($BACKEND_PID)."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

log "Repository root: $ROOT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  log "No virtual environment found. Creating one at $VENV_DIR."
  python3 -m venv "$VENV_DIR"
else
  log "Using existing virtual environment at $VENV_DIR."
fi

if [[ ! -x "$VENV_PYTHON" ]] || ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  log "Virtual environment is invalid or incomplete. Recreating $VENV_DIR."
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

ensure_node_version

log "Installing backend dependencies from $REQUIREMENTS_FILE."
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"

log "Starting FastAPI backend on http://$BACKEND_HOST:$BACKEND_PORT."
(
  cd "$ROOT_DIR"
  exec "$VENV_PYTHON" -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
) &
BACKEND_PID=$!
log "Backend running with PID $BACKEND_PID."

log "Installing frontend dependencies in $FRONTEND_DIR."
(
  cd "$FRONTEND_DIR"
  npm install
)

log "Starting Vite frontend on http://$FRONTEND_HOST:$FRONTEND_PORT."
log "Backend API is expected on http://$BACKEND_HOST:$BACKEND_PORT."
log "Frontend dev server is expected on http://$FRONTEND_HOST:$FRONTEND_PORT."
(
  cd "$FRONTEND_DIR"
  export VITE_API_BASE_URL="http://$BACKEND_HOST:$BACKEND_PORT"
  exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
)
