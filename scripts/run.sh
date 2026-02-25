#!/bin/bash
# Preacher Verse - Run Script
# Starts both backend and frontend

set -e

echo "========================================"
echo "Preacher Verse - Starting"
echo "========================================"

# Kill any existing processes on our ports
echo "Cleaning up old processes..."
lsof -ti:8080 -ti:8765 | xargs kill -9 2>/dev/null || true
sleep 1

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Start backend in background
echo "Starting backend..."
python main.py &
BACKEND_PID=$!

# Give backend time to start
sleep 2

# Start frontend
echo "Starting frontend..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "✓ System running"
echo "========================================"
echo ""
echo "Frontend:  http://localhost:3000"
echo "HTTP API:  http://localhost:8080"
echo "WebSocket: ws://localhost:8765"
echo ""
echo "Usage:"
echo "  1. Open http://localhost:3000"
echo "  2. Click 'Connect Microphone'"
echo "  3. Speak - verses will appear automatically"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap Ctrl+C and kill both processes
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Wait for either process to exit
wait
