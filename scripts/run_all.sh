#!/usr/bin/env bash
set -euo pipefail

# Run-all script for the ChatBot_Ai project
# - activates local venv if present
# - loads .env into environment
# - installs requirements (best-effort)
# - launches the FastAPI app with uvicorn

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[run_all] Project root: $ROOT_DIR"

echo "[run_all] Activating virtualenv if present..."
if [ -f "$ROOT_DIR/chatbot/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "$ROOT_DIR/chatbot/bin/activate"
  echo "[run_all] Virtualenv activated: $ROOT_DIR/chatbot"
else
  echo "[run_all] No virtualenv found at $ROOT_DIR/chatbot - continuing with system Python"
fi

if [ -f .env ]; then
  echo "[run_all] Loading .env into environment"
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

if [ -f requirements.txt ]; then
  echo "[run_all] Installing Python requirements (may ask for sudo if system pip required)"
  pip install -r requirements.txt || echo "[run_all] pip install failed or skipped"
fi

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8005}

echo "[run_all] Starting uvicorn on $HOST:$PORT"
if command -v uvicorn >/dev/null 2>&1; then
  uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
  python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi
