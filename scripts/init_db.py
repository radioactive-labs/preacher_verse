#!/usr/bin/env python3
"""Initialize the PostgreSQL database."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.database import init_db, get_session
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Initialize database tables."""
    logger.info("Initializing database...")

    try:
        init_db()
        logger.info("✓ Database initialized successfully")

        # Test connection
        session = get_session()
        logger.info("✓ Database connection verified")
        session.close()

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
