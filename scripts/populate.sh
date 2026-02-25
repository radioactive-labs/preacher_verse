#!/bin/bash
# Preacher Verse - Populate Bible Verses
# Loads all KJV verses into ChromaDB

set -e

echo "========================================"
echo "Preacher Verse - Populate Verses"
echo "========================================"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Parse arguments
FLAGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-enrich)
            FLAGS="$FLAGS --no-enrich"
            shift
            ;;
        --force-enrich)
            FLAGS="$FLAGS --force-enrich"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./scripts/populate.sh [--no-enrich] [--force-enrich]"
            exit 1
            ;;
    esac
done

echo "Enrichment: enabled by default (use --no-enrich to disable)"
echo "Flags: $FLAGS"
echo ""

python scripts/populate_verses.py $FLAGS

echo ""
echo "✓ Done"
