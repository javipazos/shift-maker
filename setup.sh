#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Shift Maker — Setup & Run ==="
echo ""

# --- Prerequisites check ---
echo "Checking prerequisites..."

if ! command -v uv &> /dev/null; then
  echo "ERROR: uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if ! command -v node &> /dev/null; then
  echo "ERROR: node not found. Install Node.js >= 18"
  exit 1
fi

echo "  uv: $(uv --version)"
echo "  node: $(node --version)"
echo ""

# --- Backend setup ---
echo "Setting up backend (Python + FastAPI)..."

if [ ! -d "$ROOT/server/.venv" ]; then
  echo "  Creating virtual environment..."
  cd "$ROOT/server"
  uv venv
fi

echo "  Installing dependencies..."
cd "$ROOT/server"
uv pip install -e ".[dev]" --quiet

echo "  Running tests..."
.venv/bin/pytest -q --no-header
echo ""

# --- Frontend setup ---
echo "Setting up frontend (React + Vite)..."

echo "  Installing dependencies..."
cd "$ROOT/client"
npm install --silent

echo ""

# --- Start ---
echo "=== Starting servers ==="
echo ""
echo "  Backend:  http://localhost:8000  (API docs: http://localhost:8000/docs)"
echo "  Frontend: http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop both."
echo ""

# Start backend in background, frontend in foreground
cd "$ROOT/server"
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM

cd "$ROOT/client"
npx vite --open
