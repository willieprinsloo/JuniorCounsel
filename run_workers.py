#!/usr/bin/env python3
"""
Start RQ workers for Junior Counsel background jobs.

Usage:
    python run_workers.py                    # Start all workers
    python run_workers.py --queue document   # Start only document processing worker
    python run_workers.py --queue draft      # Start only draft generation worker
"""
import argparse
import sys
from redis import Redis
from rq import Worker, Queue

# Add src to path
sys.path.insert(0, 'src')

from app.core.config import settings


def start_workers(queue_names: list[str]):
    """
    Start RQ workers for specified queues.

    Args:
        queue_names: List of queue names to process
    """
    if not settings.REDIS_URL:
        print("ERROR: REDIS_URL not configured in .env")
        sys.exit(1)

    # Connect to Redis
    redis_conn = Redis.from_url(str(settings.REDIS_URL))

    # Create queue objects
    queues = [Queue(name, connection=redis_conn) for name in queue_names]

    print(f"Starting RQ workers for queues: {', '.join(queue_names)}")
    print(f"Redis URL: {settings.REDIS_URL}")
    print("Listening for jobs... (Ctrl+C to stop)")

    # Start worker
    worker = Worker(queues, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start RQ workers for Junior Counsel")
    parser.add_argument(
        "--queue",
        choices=["document", "draft", "notifications", "all"],
        default="all",
        help="Which queue to process (default: all)"
    )

    args = parser.parse_args()

    # Map queue names
    queue_map = {
        "document": ["document_processing"],
        "draft": ["draft_generation"],
        "notifications": ["notifications"],
        "all": ["document_processing", "draft_generation", "notifications"]
    }

    queue_names = queue_map[args.queue]
    start_workers(queue_names)
