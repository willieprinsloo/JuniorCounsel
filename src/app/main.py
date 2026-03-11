"""
FastAPI application entry point for Junior Counsel.

This module creates the FastAPI application instance and configures:
- CORS middleware for frontend access
- API routers for all endpoints
- Application-level settings
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="Junior Counsel API",
    description="Legal document processing and drafting system for South African litigation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# TODO: Include API routers when created
# from app.api.v1 import auth, organisations, cases, documents
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# app.include_router(organisations.router, prefix="/api/v1/organisations", tags=["organisations"])
# app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
# app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
