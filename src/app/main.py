"""
FastAPI application entry point for Junior Counsel.

This module creates the FastAPI application instance and configures:
- CORS middleware for frontend access
- Request logging middleware
- Error handling middleware
- API routers for all endpoints
- Application-level settings
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.error_handler import database_error_handler, generic_error_handler

# Create FastAPI app
app = FastAPI(
    title="Junior Counsel API",
    description="Legal document processing and drafting system for South African litigation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,  # Prevent redirects that break CORS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
app.add_exception_handler(SQLAlchemyError, database_error_handler)
app.add_exception_handler(Exception, generic_error_handler)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns application status and environment info.
    """
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns welcome message and links to documentation.
    """
    return {
        "message": "Junior Counsel API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# Include API routers
from app.api.v1 import (
    auth,
    organisations,
    cases,
    documents,
    upload_sessions,
    draft_sessions,
    rulebooks,
    search,
    qa,
    chat_sessions,
    usage,
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(organisations.router, prefix="/api/v1/organisations", tags=["organisations"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(upload_sessions.router, prefix="/api/v1/upload-sessions", tags=["upload-sessions"])
app.include_router(draft_sessions.router, prefix="/api/v1/draft-sessions", tags=["draft-sessions"])
app.include_router(rulebooks.router, prefix="/api/v1/rulebooks", tags=["rulebooks"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["qa"])
app.include_router(chat_sessions.router, prefix="/api/v1/chat-sessions", tags=["chat-sessions"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
