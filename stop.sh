#!/bin/bash

# Stop script for Preacher Verse

echo "Stopping Preacher Verse..."

# Function to kill a process and its children
kill_process_tree() {
    local pid=$1
    local name=$2

    if kill -0 $pid 2>/dev/null; then
        echo "Stopping $name (PID: $pid)..."

        # Get child processes
        local children=$(pgrep -P $pid 2>/dev/null || true)

        # Kill children first
        if [ -n "$children" ]; then
            echo "  Stopping child processes: $children"
            kill $children 2>/dev/null || true
        fi

        # Kill main process
        kill $pid 2>/dev/null || true

        # Wait a bit, then force kill if still alive
        sleep 1
        if kill -0 $pid 2>/dev/null; then
            echo "  Force stopping $name..."
            kill -9 $pid 2>/dev/null || true
        fi

        echo "✓ $name stopped"
    else
        echo "✗ $name not running (PID: $pid)"
    fi
}

# Stop backend from PID file
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill_process_tree $BACKEND_PID "Backend"
    rm .backend.pid
fi

# Stop frontend from PID file
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill_process_tree $FRONTEND_PID "Frontend"
    rm .frontend.pid
fi

# Clean up orphaned processes on our ports (safety check)
echo "Checking for orphaned processes..."

# Kill any Python processes on port 7860 (backend/Pipecat)
PORT_7860_PID=$(lsof -ti:7860 2>/dev/null || true)
if [ -n "$PORT_7860_PID" ]; then
    # Only kill if it's a Python process from this directory
    for pid in $PORT_7860_PID; do
        CMD=$(ps -p $pid -o command= 2>/dev/null || true)
        if [[ "$CMD" == *"main.py"* ]] || [[ "$CMD" == *"preacher_verse"* ]]; then
            echo "  Stopping orphaned backend process (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
        fi
    done
fi

# Kill any Node processes on port 3000 (React frontend)
PORT_3000_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$PORT_3000_PID" ]; then
    for pid in $PORT_3000_PID; do
        CMD=$(ps -p $pid -o command= 2>/dev/null || true)
        if [[ "$CMD" == *"react-scripts"* ]] || [[ "$CMD" == *"node"* ]]; then
            echo "  Stopping orphaned frontend process (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
        fi
    done
fi

# Kill WebSocket server on 8765
PORT_8765_PID=$(lsof -ti:8765 2>/dev/null || true)
if [ -n "$PORT_8765_PID" ]; then
    for pid in $PORT_8765_PID; do
        CMD=$(ps -p $pid -o command= 2>/dev/null || true)
        if [[ "$CMD" == *"python"* ]] && [[ "$CMD" == *"preacher_verse"* ]]; then
            echo "  Stopping orphaned WebSocket process (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
        fi
    done
fi

echo "✓ All services stopped"
