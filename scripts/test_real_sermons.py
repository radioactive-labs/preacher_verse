#!/usr/bin/env python3
"""Test DSPy signatures with real sermon transcripts."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
from backend.dspy import FetchRelevantVerse
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


# Real sermon excerpts from Berean Bible Church - Matthew 6:25-34
REAL_SERMON_EXCERPTS = [
    {
        "title": "Anxiety is Unbelief",
        "context": "Anxiety is unbelief! It is a failure to trust God to care for us. The way you deal with anxiety and stress is a reflection of your view of God. If you know God, if you know that He is omnipresent, omniscience, all powerful; and if you understand that He is on your side, why would you ever worry?",
        "expected_theme": "anxiety as failure to trust God",
        "expected_verses": ["Matthew 6:27", "Matthew 6:25-34", "Philippians 4:6-7", "1 Peter 5:7"],
        "topic": "worry/anxiety"
    },
    {
        "title": "Trust God for Provisions",
        "context": "If you can't do the least thing to provide for yourself, why don't you trust God for all your provisions? 'Is not life more than food and the body more than clothing?' If God has provided for the greater necessities, why can't we trust Him for the little things?",
        "expected_theme": "trusting God for provision daily needs",
        "expected_verses": ["Matthew 6:25", "Matthew 6:33", "Luke 12:24", "Philippians 4:19"],
        "topic": "God's provision"
    },
    {
        "title": "God Loves and Cares",
        "context": "If we are going to conquer worry, we must come to the realization that God loves us, and that He will take care of us. So many people are simply not convinced of this fact. But if you really believe that God is in charge, and that He loves you and will meet your needs, then you can relax in faith.",
        "expected_theme": "God's love and care conquering worry",
        "expected_verses": ["1 Peter 5:7", "Matthew 6:26", "Romans 8:28", "Psalm 55:22"],
        "topic": "God's love/care"
    },
]


def test_real_sermon_analysis():
    """Test the complete pipeline with real sermon excerpts."""
    logger.info("="*80)
    logger.info("TESTING WITH REAL SERMON TRANSCRIPTS")
    logger.info("="*80)
    logger.info("Source: Berean Bible Church - 'Do Not Be Anxious' (Matthew 6:25-34)")
    logger.info("="*80)

    # Initialize the full pipeline
    fetch_verse = FetchRelevantVerse()

    for i, excerpt in enumerate(REAL_SERMON_EXCERPTS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST {i}: {excerpt['title']}")
        logger.info(f"{'='*80}")
        logger.info(f"\nSermon Context:")
        logger.info(f'"{excerpt["context"]}"')
        logger.info(f"\nExpected Theme: {excerpt['expected_theme']}")
        logger.info(f"Likely Good Verses: {', '.join(excerpt['expected_verses'])}")

        # Run the full pipeline
        logger.info(f"\n--- Running FetchRelevantVerse Pipeline ---")

        try:
            result = fetch_verse(context=excerpt["context"], excluded_references=[])

            if result:
                logger.info(f"\n✓ VERSE RETRIEVED:")
                logger.info(f"  Reference: {result['verse_reference']}")
                logger.info(f"  Text: {result['verse_text']}")
                logger.info(f"  Theme Detected: {result['theme']}")
                logger.info(f"  Relevance Score: {result['relevance_score']}")
                logger.info(f"  Why Relevant: {result['why_relevant'][:150]}...")

                # Check if it's one of the expected verses
                if result['verse_reference'] in excerpt['expected_verses']:
                    logger.info(f"\n  🎯 EXCELLENT! Retrieved one of the expected verses!")
                elif any(expected.split(':')[0] in result['verse_reference'] for expected in excerpt['expected_verses']):
                    logger.info(f"\n  ✓ GOOD! Retrieved a verse from the expected passage")
                else:
                    logger.info(f"\n  ⚠️  Retrieved different verse than expected (but may still be valid)")

                # Check relevance score
                if result['relevance_score'] >= 85:
                    logger.info(f"  ✓ High relevance score (85+)")
                elif result['relevance_score'] >= 70:
                    logger.info(f"  ✓ Good relevance score (70+)")
                else:
                    logger.info(f"  ⚠️  Lower relevance score (<70)")

            else:
                logger.info(f"\n✗ NO VERSE RETRIEVED")
                logger.info(f"  Possible reasons:")
                logger.info(f"  - Edge case detected (scripture quote, admin, etc.)")
                logger.info(f"  - No theme extracted")
                logger.info(f"  - No verses with high enough relevance")

        except Exception as e:
            logger.error(f"\n✗ ERROR: {e}", exc_info=True)

    logger.info(f"\n{'='*80}")
    logger.info("TESTING COMPLETE")
    logger.info(f"{'='*80}")


def test_edge_cases():
    """Test edge case detection with real-world examples."""
    logger.info("\n\n")
    logger.info("="*80)
    logger.info("TESTING EDGE CASE DETECTION")
    logger.info("="*80)

    fetch_verse = FetchRelevantVerse()

    edge_cases = [
        {
            "title": "Scripture Quote Detection",
            "context": "Turn with me to Matthew 6:27. Jesus says 'Can any one of you by worrying add a single hour to your life?' This is such a powerful question.",
            "should_skip": True,
            "reason": "Pastor is reading scripture directly"
        },
        {
            "title": "Administrative Announcement",
            "context": "Before we continue, just a reminder that coffee and fellowship are in the lobby after service. Also, small groups meet on Wednesday evenings at 7pm.",
            "should_skip": True,
            "reason": "Church logistics, not sermon content"
        },
        {
            "title": "Valid Theological Content",
            "context": "When trials come into your life, God doesn't promise to remove them immediately. But He promises to be with you in the fire, walking beside you through every difficulty.",
            "should_skip": False,
            "reason": "Clear theological teaching about God's presence in trials"
        }
    ]

    for i, test_case in enumerate(edge_cases, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"EDGE CASE TEST {i}: {test_case['title']}")
        logger.info(f"{'='*80}")
        logger.info(f'Context: "{test_case["context"]}"')
        logger.info(f"Expected: {'SKIP' if test_case['should_skip'] else 'PROCESS'}")
        logger.info(f"Reason: {test_case['reason']}")

        result = fetch_verse(context=test_case["context"], excluded_references=[])

        actually_skipped = (result is None)

        logger.info(f"\nResult: {'SKIPPED' if actually_skipped else 'PROCESSED'}")

        if actually_skipped == test_case['should_skip']:
            logger.info(f"✓ CORRECT - Edge case detection working as expected!")
        else:
            logger.info(f"✗ INCORRECT - Edge case detection failed!")
            if not actually_skipped and result:
                logger.info(f"  Retrieved: {result['verse_reference']}")

    logger.info(f"\n{'='*80}")


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test with real sermon transcripts")
    parser.add_argument(
        "--test",
        choices=["sermons", "edges", "both"],
        default="both",
        help="Which tests to run"
    )

    args = parser.parse_args()

    if args.test in ["sermons", "both"]:
        test_real_sermon_analysis()

    if args.test in ["edges", "both"]:
        test_edge_cases()

    logger.info("\n✓ All tests complete!")


if __name__ == "__main__":
    main()
