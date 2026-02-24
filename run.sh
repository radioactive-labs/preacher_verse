#!/bin/bash

# Startup script for Preacher Verse
# Runs backend server with WebRTC support

set -e

echo "=================================="
echo "Preacher Verse - Starting System"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "✗ No .env file found. Run ./quickstart.sh first."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Pre-create log files to avoid race condition
touch logs/backend.log
touch logs/frontend.log

# Activate virtual environment
echo "Activating Python virtual environment..."
source venv/bin/activate

# Start backend in background with Pipecat runner
echo "Starting Pipecat bot server with SmallWebRTC..."
nohup python main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"

# Start React frontend in background
echo "Starting React frontend..."
cd frontend
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✓ Frontend started (PID: $FRONTEND_PID)"

# Wait for servers to initialize
sleep 5

echo ""
echo "=================================="
echo "✓ System Running"
echo "=================================="
echo ""
echo "Pipecat Bot:     http://localhost:7860 (Backend with /api/offer)"
echo "React Frontend:  http://localhost:3000 (Open this in your browser)"
echo "WebSocket:       ws://localhost:8765"
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  Backend:  tail -f logs/backend.log"
echo "  Frontend: tail -f logs/frontend.log"
echo ""
echo "To stop:"
echo "  ./stop.sh  (or kill $BACKEND_PID $FRONTEND_PID)"
echo ""

# Save PIDs to file for stop script
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo "Tailing backend logs (Ctrl+C to exit)..."
echo ""
tail -f logs/backend.log
