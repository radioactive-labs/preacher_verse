#!/usr/bin/env python3
"""Test connections to all required services."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.dspy import FetchRelevantVerse
from backend.utils.logger import setup_logger
from backend.utils.config import config
import google.generativeai as genai

logger = setup_logger(__name__)


def test_deepgram():
    """Test Deepgram API key is set."""
    logger.info("Testing Deepgram configuration...")
    try:
        if not config.DEEPGRAM_API_KEY:
            logger.error("✗ DEEPGRAM_API_KEY not set")
            return False

        # Just verify the key format (starts with expected prefix)
        if len(config.DEEPGRAM_API_KEY) < 20:
            logger.error("✗ DEEPGRAM_API_KEY appears invalid (too short)")
            return False

        logger.info("✓ Deepgram API key configured")
        return True
    except Exception as e:
        logger.error(f"✗ Deepgram check failed: {e}")
        return False


def test_gemini():
    """Test Gemini API connection."""
    logger.info("Testing Gemini API connection...")
    try:
        if not config.GEMINI_API_KEY:
            logger.error("✗ GEMINI_API_KEY not set")
            return False

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'connected' if you can read this.")

        if response.text:
            logger.info("✓ Gemini API connected successfully")
            logger.info(f"  Response: {response.text.strip()[:50]}")
            return True
        else:
            logger.error("✗ Gemini API response empty")
            return False
    except Exception as e:
        logger.error(f"✗ Gemini API connection failed: {e}")
        return False


def test_chromadb():
    """Test ChromaDB connection."""
    logger.info("Testing ChromaDB connection...")
    try:
        fetch_verse = FetchRelevantVerse()
        stats = fetch_verse.get_collection_stats()

        logger.info(f"✓ ChromaDB connected successfully")
        logger.info(f"  Collection: {stats['collection_name']}")
        logger.info(f"  Total verses: {stats['total_verses']}")

        if stats['total_verses'] > 0:
            logger.info(f"  ✓ Collection has verses")
        else:
            logger.warning(f"  ⚠ Collection is empty (run populate_verses.py)")

        return True
    except Exception as e:
        logger.error(f"✗ ChromaDB connection failed: {e}")
        return False


def main():
    """Run all connection tests."""
    logger.info("=" * 60)
    logger.info("Testing Service Connections")
    logger.info("=" * 60)

    results = {
        'Deepgram': test_deepgram(),
        'Gemini': test_gemini(),
        'ChromaDB': test_chromadb()
    }

    logger.info("\n" + "=" * 60)
    logger.info("Connection Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for service, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{service:15} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("All tests passed! System is ready.")
        sys.exit(0)
    else:
        logger.error("Some tests failed. Please check configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
