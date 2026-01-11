"""
Database configuration and session management for ParagonOCR Web Edition.

Uses SQLAlchemy ORM with SQLite database in WAL mode for better concurrency.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

from app.config import settings

# Create database directory if it doesn't exist
db_dir = os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", ""))
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Create SQLAlchemy engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    connect_args=connect_args,
)

# Enable WAL mode for SQLite (better concurrency)
# @event.listens_for(engine, "connect")
# def set_sqlite_pragma(dbapi_conn, connection_record):
#     """Enable WAL mode for SQLite database."""
#     cursor = dbapi_conn.cursor()
#     try:
#         cursor.execute("PRAGMA journal_mode=WAL")
#         cursor.close()
#     except Exception as e:
#         # Fallback for systems where WAL is not supported (e.g. WSL mounted drives)
#         print(f"WARNING: Could not enable WAL mode: {e}")
#         pass

# Base class for declarative models
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database by creating all tables.
    """
    # Import models to ensure they're registered
    from app.models import receipt, product, category, shop, webauthn_key, user
    
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Dependency for getting database session.
    Use in FastAPI route dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session.
    Use for non-FastAPI contexts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

