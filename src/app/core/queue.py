"""
Queue configuration and job enqueuing for background workers.

Uses RQ (Redis Queue) for durable job processing.
"""
import logging
from typing import Optional

try:
    from redis import Redis
    from rq import Queue
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    logging.warning("Redis/RQ not installed. Queue operations will be disabled.")

from app.core.config import settings

# Redis connection (lazily initialized)
_redis_conn: Optional[Redis] = None


def get_redis_connection():
    """
    Get Redis connection (singleton pattern).

    Returns:
        Redis connection instance

    Raises:
        RuntimeError: If Redis/RQ not available
    """
    if not RQ_AVAILABLE:
        raise RuntimeError("Redis/RQ not installed. Install with: pip install redis rq")

    global _redis_conn
    if _redis_conn is None:
        if settings.REDIS_URL is None:
            raise ValueError("REDIS_URL not configured in settings")
        _redis_conn = Redis.from_url(str(settings.REDIS_URL))
    return _redis_conn


# Queue definitions
def get_document_queue():
    """
    Get the document processing queue.

    Handles: OCR, text extraction, chunking, embedding, indexing, classification
    """
    return Queue('document_processing', connection=get_redis_connection())


def get_draft_queue():
    """
    Get the draft generation queue.

    Handles: RAG research, LLM drafting, citation extraction
    """
    return Queue('draft_generation', connection=get_redis_connection())


def get_notification_queue():
    """
    Get the notification queue.

    Handles: Email sending, in-app notifications
    """
    return Queue('notifications', connection=get_redis_connection())


# Job enqueuing helpers
def enqueue_document_processing(document_id: str, job_timeout: str = '30m') -> str:
    """
    Enqueue a document processing job.

    Args:
        document_id: Document ID (UUID)
        job_timeout: Job timeout (e.g., '30m', '1h')

    Returns:
        Job ID
    """
    from app.workers.document_processing import process_document_job

    queue = get_document_queue()
    job = queue.enqueue(
        process_document_job,
        document_id,
        job_timeout=job_timeout,
        result_ttl=86400  # Keep result for 24 hours
    )
    return job.id


def enqueue_draft_research(draft_session_id: str, job_timeout: str = '10m') -> str:
    """
    Enqueue a draft research job (RAG search).

    Args:
        draft_session_id: DraftSession ID (UUID)
        job_timeout: Job timeout

    Returns:
        Job ID
    """
    from app.workers.draft_generation import draft_research_job

    queue = get_draft_queue()
    job = queue.enqueue(
        draft_research_job,
        draft_session_id,
        job_timeout=job_timeout,
        result_ttl=86400
    )
    return job.id


def enqueue_draft_generation(draft_session_id: str, job_timeout: str = '15m') -> str:
    """
    Enqueue a draft generation job (LLM drafting).

    Args:
        draft_session_id: DraftSession ID (UUID)
        job_timeout: Job timeout

    Returns:
        Job ID
    """
    from app.workers.draft_generation import draft_generation_job

    queue = get_draft_queue()
    job = queue.enqueue(
        draft_generation_job,
        draft_session_id,
        job_timeout=job_timeout,
        result_ttl=86400
    )
    return job.id
