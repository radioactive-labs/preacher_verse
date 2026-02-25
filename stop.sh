#!/bin/bash
# Stop Preacher Verse services

echo "Stopping Preacher Verse..."

# Kill processes on known ports
for port in 3000 8080 8765; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Stopping processes on port $port: $pids"
        kill $pids 2>/dev/null || true
    fi
done

echo "✓ Stopped"
