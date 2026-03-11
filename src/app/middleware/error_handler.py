"""
Error handling middleware for FastAPI.

Provides consistent error responses across the API.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database errors and return appropriate HTTP responses.

    Args:
        request: The incoming request
        exc: The database exception

    Returns:
        JSONResponse with error details
    """
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Database constraint violation",
                "detail": "The requested operation violates a database constraint",
                "code": 409
            }
        )

    # Generic database error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database error",
            "detail": "An error occurred while accessing the database",
            "code": 500
        }
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic exceptions and return appropriate HTTP responses.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "code": 500
        }
    )
