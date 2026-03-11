"""
Database session middleware for FastAPI.

Provides database session management as a dependency.
"""
from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Yields a SQLAlchemy session and ensures it's closed after use.
    Automatically commits on success and rolls back on error.

    Usage:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
