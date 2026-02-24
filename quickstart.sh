#!/bin/bash

# Quickstart script for Preacher Verse

set -e

echo "=================================="
echo "Preacher Verse - Quick Start"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your API keys before continuing!"
    echo "   Required: DEEPGRAM_API_KEY, GEMINI_API_KEY, PINECONE_API_KEY"
    echo ""
    echo "Run this script again after updating .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "✗ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "Starting infrastructure services..."
docker-compose up -d postgres redis

echo "Waiting for services to be ready..."
sleep 10

echo ""
echo "Initializing database..."
python scripts/init_db.py

echo ""
echo "Populating verses..."
python scripts/populate_verses.py

echo ""
echo "Testing connections..."
python scripts/test_connection.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ Setup complete!"
    echo "=================================="
    echo ""
    echo "To run the system:"
    echo ""
    echo "  Terminal 1 (Backend):"
    echo "    python main.py test"
    echo ""
    echo "  Terminal 2 (Frontend):"
    echo "    cd frontend && npm install && npm start"
    echo ""
    echo "  Then open: http://localhost:3000"
    echo ""
else
    echo ""
    echo "✗ Setup failed. Please check the errors above."
    exit 1
fi
