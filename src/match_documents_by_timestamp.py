"""
Match and populate file_path for documents based on file modification timestamps.

This script matches documents in the database (that are missing file_path)
with files in the upload directories by comparing timestamps.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.persistence.models import Document

def get_file_mtime_utc(file_path: str) -> datetime:
    """Get file modification time as UTC datetime."""
    stat = os.stat(file_path)
    # Convert timestamp to UTC datetime
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

def match_documents_by_timestamp():
    """Match documents to files by comparing timestamps (within 1 second tolerance)."""

    upload_dir = settings.UPLOAD_FOLDER or "/Users/wlprinsloo/Documents/Projects/JuniorCounsel/uploads"

    # Create database connection
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Find documents without file_path
        documents = db.query(Document).filter(Document.file_path.is_(None)).all()

        print(f"Found {len(documents)} documents without file_path\n")

        matched_count = 0
        unmatched_count = 0

        for doc in documents:
            case_dir = Path(upload_dir) / str(doc.case_id)

            if not case_dir.exists():
                print(f"⚠ Case directory not found: {case_dir}")
                unmatched_count += 1
                continue

            # Look for a file with matching timestamp (within 1 second)
            doc_created_at = doc.created_at.replace(tzinfo=timezone.utc)

            matched_file = None
            for file_path in case_dir.glob("*.pdf"):
                file_mtime = get_file_mtime_utc(str(file_path))
                time_diff = abs((file_mtime - doc_created_at).total_seconds())

                if time_diff < 1.0:  # Within 1 second
                    matched_file = file_path
                    break

            if matched_file:
                # Get file size
                file_size = matched_file.stat().st_size

                # Update document
                doc.file_path = str(matched_file)
                doc.file_size = file_size
                db.flush()

                print(f"✓ Matched document {doc.id}")
                print(f"  Filename: {doc.filename}")
                print(f"  File: {matched_file.name}")
                print(f"  Size: {file_size:,} bytes")
                print(f"  DB time: {doc_created_at}")
                print(f"  File time: {get_file_mtime_utc(str(matched_file))}")
                print()

                matched_count += 1
            else:
                print(f"✗ No matching file for document {doc.id}")
                print(f"  Filename: {doc.filename}")
                print(f"  Expected time: {doc_created_at}")
                print()
                unmatched_count += 1

        # Commit changes
        db.commit()

        print(f"{'='*60}")
        print(f"Summary:")
        print(f"  Successfully matched: {matched_count}")
        print(f"  Unmatched: {unmatched_count}")
        print(f"{'='*60}")

        return matched_count, unmatched_count

    finally:
        db.close()

if __name__ == "__main__":
    matched, unmatched = match_documents_by_timestamp()
    sys.exit(0 if unmatched == 0 else 1)
