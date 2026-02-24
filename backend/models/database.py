from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path
from backend.utils.config import config

Base = declarative_base()

class Verse(Base):
    """Bible verse model."""
    __tablename__ = 'verses'

    id = Column(Integer, primary_key=True)
    book = Column(String(50), nullable=False)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    reference = Column(String(100), unique=True, nullable=False)  # e.g., "John 3:16"
    text = Column(Text, nullable=False)
    enriched_text = Column(Text, default='')  # Contextual enrichment from LLM
    manual_tags = Column(String(500), default='')  # Comma-separated tags for SQLite
    popularity_score = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Verse {self.reference}>"

    def to_dict(self):
        return {
            'id': self.id,
            'book': self.book,
            'chapter': self.chapter,
            'verse': self.verse,
            'reference': self.reference,
            'text': self.text,
            'enriched_text': self.enriched_text,
            'manual_tags': self.manual_tags.split(',') if self.manual_tags else [],
            'popularity_score': self.popularity_score
        }

# Database connection
def get_engine():
    """Create SQLite database engine."""
    # Use SQLite database in data directory
    db_dir = Path(__file__).parent.parent.parent / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "verses.sqlite"

    # SQLite connection string
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url, echo=False)

def get_session():
    """Create database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
