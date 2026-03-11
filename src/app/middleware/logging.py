"""
Request logging middleware for FastAPI.

Logs all incoming requests with timing information.
"""
import time
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests with timing information.

    Logs:
    - Request method and path
    - Response status code
    - Request duration in milliseconds
    - Client IP address
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log details.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response from the next handler
        """
        start_time = time.time()

        # Extract client IP (considering proxies)
        client_ip = request.client.host if request.client else "unknown"
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            client_ip = forwarded_for.split(",")[0].strip()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request details
        logger.info(
            f"{request.method} {request.url.path} "
            f"[{response.status_code}] "
            f"{duration_ms:.2f}ms "
            f"client={client_ip}"
        )

        return response
