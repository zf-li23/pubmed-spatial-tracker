#!/bin/bash
set -e

echo "==================================="
echo " Starting PubMed Spatial Tracker "
echo "==================================="

cd "$(dirname "$0")" # Go to root of project

# Step 1: Frontend build if needed
echo "=> Checking frontend build..."
cd frontend
if [ ! -d "dist" ] || [ "$(git diff --name-only src/)" ]; then
    echo "   Rebuilding frontend assets..."
    npm run build
else
    echo "   Frontend up to date."
fi
cd ../../

# Step 2: Clean up zombie port 8000 processes SAFELY
echo "=> Cleaning up any processes on port 8000..."
PORT_PIDS=$(lsof -t -i:8000 || true)
if [ ! -z "$PORT_PIDS" ]; then
    echo "   Found processes holding port 8000: $PORT_PIDS"
    echo "   Sending graceful termination signal (kill -15)..."
    kill -15 $PORT_PIDS
    sleep 2
    
    # Check if they are still alive
    PORT_PIDS_REMAINING=$(lsof -t -i:8000 || true)
    if [ ! -z "$PORT_PIDS_REMAINING" ]; then
        echo "   Processes still running. Forcing termination (kill -9)..."
        kill -9 $PORT_PIDS_REMAINING
        sleep 1
    fi
fi

# Step 3: Run FastAPI
echo "=> Starting FastAPI Server..."
cd web_app
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
