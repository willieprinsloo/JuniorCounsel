"""
Script to retry processing for documents stuck in QUEUED status.

This script finds documents that failed to enqueue (typically due to Redis being down)
and retries enqueueing them for processing.
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.queue import enqueue_document_processing
from app.persistence.models import DocumentStatusEnum

def retry_stuck_documents():
    """Retry processing for documents stuck in QUEUED status with errors."""
    # Create database connection
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Find documents stuck in QUEUED with error messages
        from app.persistence.models import Document

        # Get all queued documents with errors
        query = db.query(Document).filter(
            Document.overall_status == DocumentStatusEnum.QUEUED,
            Document.error_message.isnot(None)
        )

        stuck_documents = query.all()

        print(f"Found {len(stuck_documents)} stuck documents")

        retried_count = 0
        failed_count = 0

        for doc in stuck_documents:
            print(f"\nRetrying document: {doc.id} ({doc.filename})")
            print(f"  Error was: {doc.error_message}")

            try:
                # Clear error message
                doc.error_message = None
                db.flush()

                # Enqueue processing job
                job_id = enqueue_document_processing(doc.id)

                db.flush()
                db.commit()

                print(f"  ✓ Successfully enqueued with job ID: {job_id}")
                retried_count += 1

            except Exception as e:
                print(f"  ✗ Failed to enqueue: {str(e)}")
                doc.error_message = f"Retry failed: {str(e)}"
                db.flush()
                db.commit()
                failed_count += 1

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Total stuck documents: {len(stuck_documents)}")
        print(f"  Successfully retried: {retried_count}")
        print(f"  Failed to retry: {failed_count}")
        print(f"{'='*60}")

        return retried_count, failed_count

    finally:
        db.close()

if __name__ == "__main__":
    retried, failed = retry_stuck_documents()
    sys.exit(0 if failed == 0 else 1)
