#!/bin/bash
# Preacher Verse - Setup Script
# Run this once after cloning the repository

set -e

echo "========================================"
echo "Preacher Verse - Setup"
echo "========================================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - DEEPGRAM_API_KEY"
    echo "   - GEMINI_API_KEY"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if API keys are set
source .env
if [ -z "$DEEPGRAM_API_KEY" ] || [ "$DEEPGRAM_API_KEY" = "your_deepgram_api_key_here" ]; then
    echo "⚠️  DEEPGRAM_API_KEY not set in .env"
    exit 1
fi
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "⚠️  GEMINI_API_KEY not set in .env"
    exit 1
fi

echo "✓ API keys configured"

# Install frontend dependencies
if [ -d "frontend" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Populate Bible verses if ChromaDB is empty
if [ ! -d "data/chromadb" ] || [ ! -f "data/chromadb/chroma.sqlite3" ]; then
    echo ""
    echo "Populating Bible verses with enrichment (this takes ~30 min on first run)..."
    echo "Use --no-enrich for faster setup without enrichment."
    python scripts/populate_verses.py
else
    echo "✓ ChromaDB already populated"
fi

# Test connections
echo ""
echo "Testing connections..."
python scripts/test_connection.py

echo ""
echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "To start the system:"
echo "  ./scripts/run.sh"
echo ""
echo "Or manually:"
echo "  Terminal 1: python main.py"
echo "  Terminal 2: cd frontend && npm start"
echo ""
