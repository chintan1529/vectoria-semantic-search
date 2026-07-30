#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║          Vectoria Production Platform                ║"
echo "╚══════════════════════════════════════════════════════╝"

# Start the backend
echo "[Vectoria] Starting Backend (port 8000)..."
cd /app
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 &

# Start the frontend
echo "[Vectoria] Starting Frontend (port 3000)..."
cd /app/frontend
npx next start -p 3000 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
