#!/usr/bin/env python3
"""Test the verse enricher."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.verse_enricher import VerseEnricher
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def test_enricher():
    """Test enriching a few sample verses."""

    # Sample verses to test
    test_verses = [
        ("John 3:16", "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."),
        ("Psalm 23:1", "The LORD is my shepherd; I shall not want."),
        ("Romans 8:28", "And we know that all things work together for good to them that love God, to them who are the called according to his purpose."),
    ]

    logger.info("Initializing VerseEnricher...")
    enricher = VerseEnricher()

    logger.info("\n" + "="*80)
    logger.info("Testing verse enrichment:")
    logger.info("="*80 + "\n")

    for reference, text in test_verses:
        logger.info(f"\nReference: {reference}")
        logger.info(f"Original: {text}")

        enriched = enricher.enrich_verse(reference, text)

        logger.info(f"Enriched: {enriched}")
        logger.info("-" * 80)

    logger.info("\n✓ Enrichment test completed!")

if __name__ == "__main__":
    test_enricher()
