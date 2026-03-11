# Phase 2 - Implementation Plan

**Project:** Junior Counsel Legal Document Processing System
**Phase:** Phase 2 - Middleware, Authentication, and Core APIs
**Estimated Effort:** 3-4 weeks
**Start Date:** TBD
**Target Completion:** TBD

---

## Executive Summary

Phase 2 builds the REST API layer on top of the Phase 1 backend foundation. This phase delivers 27 REST endpoints with authentication, authorization, and proper middleware, enabling frontend integration and setting the stage for Phase 3 worker implementation.

### Key Deliverables

1. **Flask or FastAPI Application** - RESTful API framework with async support
2. **Authentication System** - JWT-based authentication for secure access
3. **Authorization Middleware** - Role-based access control and organisation scoping
4. **27 REST Endpoints** - Complete CRUD operations for all entities
5. **Request/Response Validation** - Pydantic schemas for all endpoints
6. **Error Handling** - Standardized JSON error responses
7. **API Documentation** - Swagger/OpenAPI interactive documentation
8. **Integration Tests** - Comprehensive endpoint testing (≥80% coverage)

---

## Technology Stack

### Framework Decision: FastAPI (Recommended)

**FastAPI Advantages:**
- ✅ Native async/await support (critical for Phase 3 workers)
- ✅ Automatic OpenAPI/Swagger documentation
- ✅ Pydantic integration (we're already using it)
- ✅ High performance (on par with Node.js/Go)
- ✅ Type hints everywhere (matches our Phase 1 style)
- ✅ Modern, active community

**Flask Alternative:**
- ✅ More mature ecosystem
- ✅ Simpler for small APIs
- ❌ No native async (requires Flask-AIOHTTP or Quart)
- ❌ Manual Swagger setup (Flask-RESTX or flasgger)
- ⚠️ Slower than FastAPI for high-throughput

**Recommendation:** **FastAPI** for better async support and auto-documentation

### Additional Dependencies

```txt
# Core Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0  # ASGI server

# Authentication
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4  # Password hashing
python-multipart==0.0.9  # File uploads

# Database (already have SQLAlchemy)
# psycopg2-binary  # Already in Phase 1

# Validation (already have Pydantic)
# pydantic  # Already in Phase 1
email-validator==2.1.0  # Email validation

# Testing
pytest-asyncio==0.23.3  # Async test support
httpx==0.26.0  # Async HTTP client for testing

# Queue (Phase 2.3)
redis==5.0.1
rq==1.15.1  # Redis Queue (simple, production-ready)

# CORS (for frontend)
# (built into FastAPI)

# Development
black==24.1.0  # Code formatting
mypy==1.8.0  # Type checking
```

---

## Phase 2 Sub-Phases

### Phase 2.1: Foundation and Middleware (Week 1)

**Goal:** Set up FastAPI application structure with core middleware

**Tasks:**
1. Set up FastAPI application structure
2. Implement database session middleware
3. Implement error handling middleware
4. Implement request logging middleware
5. Set up CORS for frontend integration
6. Create basic health check endpoint

**Deliverables:**
- `src/app/main.py` - FastAPI application entry point
- `src/app/middleware/` - Middleware modules
- `src/app/core/security.py` - Security utilities
- Basic integration test setup

**Estimated Effort:** 3-4 days

---

### Phase 2.2: Authentication and Authorization (Week 1-2)

**Goal:** Implement JWT-based authentication system

**Tasks:**
1. Implement password hashing utilities
2. Create JWT token generation/validation
3. Implement authentication dependency
4. Create user registration endpoint
5. Create login endpoint
6. Implement role-based authorization decorator
7. Implement organisation scoping validation

**Deliverables:**
- `src/app/api/v1/auth.py` - Auth endpoints
- `src/app/dependencies.py` - Dependency injection (get_current_user, etc.)
- `src/app/schemas/auth.py` - Pydantic schemas
- Auth integration tests

**Estimated Effort:** 4-5 days

---

### Phase 2.3: Core CRUD Endpoints (Week 2-3)

**Goal:** Implement all 27 REST endpoints

**Priority 1 - Organisation & User (Days 1-2):**
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/users/me
- GET /api/v1/organisations
- POST /api/v1/organisations
- GET /api/v1/organisations/{id}
- POST /api/v1/organisations/{id}/users
- DELETE /api/v1/organisations/{org_id}/users/{user_id}

**Priority 2 - Cases (Days 3-4):**
- GET /api/v1/cases (paginated)
- POST /api/v1/cases
- GET /api/v1/cases/{id}
- PATCH /api/v1/cases/{id}
- DELETE /api/v1/cases/{id}

**Priority 3 - Documents (Days 5-6):**
- GET /api/v1/documents (paginated)
- POST /api/v1/documents (file upload)
- GET /api/v1/documents/{id}
- PATCH /api/v1/documents/{id}
- DELETE /api/v1/documents/{id}
- GET /api/v1/documents/{id}/download

**Priority 4 - Upload Sessions (Day 7):**
- GET /api/v1/upload-sessions (paginated)
- POST /api/v1/upload-sessions
- GET /api/v1/upload-sessions/{id}

**Priority 5 - Draft Sessions (Days 8-9):**
- GET /api/v1/draft-sessions (paginated)
- POST /api/v1/draft-sessions
- GET /api/v1/draft-sessions/{id}
- POST /api/v1/draft-sessions/{id}/answers
- POST /api/v1/draft-sessions/{id}/generate

**Priority 6 - Rulebooks (Day 10):**
- GET /api/v1/rulebooks (paginated, admin only)
- POST /api/v1/rulebooks (admin only)
- GET /api/v1/rulebooks/{id}
- PUT /api/v1/rulebooks/{id} (admin only)
- POST /api/v1/rulebooks/{id}/publish (admin only)
- POST /api/v1/rulebooks/{id}/deprecate (admin only)

**Deliverables:**
- `src/app/api/v1/` - All endpoint routers
- `src/app/schemas/` - All Pydantic schemas
- Integration tests for all endpoints

**Estimated Effort:** 10-12 days

---

### Phase 2.4: Queue Integration Stubs (Week 3-4)

**Goal:** Add Redis/RQ integration for async operations

**Tasks:**
1. Set up Redis connection
2. Create RQ queue configuration
3. Implement job enqueuing functions (stubs for Phase 3)
4. Update endpoints to return 202 Accepted for async operations
5. Create job status tracking endpoints

**Deliverables:**
- `src/app/core/queue.py` - Queue configuration
- `src/app/workers/` - Worker job stubs (implemented in Phase 3)
- Queue integration tests

**Estimated Effort:** 3-4 days

---

### Phase 2.5: Testing and Documentation (Week 4)

**Goal:** Comprehensive testing and API documentation

**Tasks:**
1. Write integration tests for all endpoints
2. Test authentication enforcement
3. Test organisation scoping (prevent cross-org access)
4. Test pagination edge cases
5. Generate and review OpenAPI documentation
6. Update NEXT_STEPS.md for Phase 3 transition

**Deliverables:**
- ≥80% test coverage for API layer
- Swagger/OpenAPI documentation accessible at /docs
- Phase 3 transition guide

**Estimated Effort:** 3-4 days

---

## Project Structure (Phase 2)

```
src/app/
├── __init__.py
├── main.py                     # FastAPI app entry point
├── core/
│   ├── __init__.py
│   ├── config.py               # Pydantic settings (Phase 1)
│   ├── db.py                   # Database session (Phase 1)
│   ├── security.py             # NEW: JWT, password hashing
│   └── queue.py                # NEW: Redis/RQ configuration
├── middleware/
│   ├── __init__.py
│   ├── database.py             # NEW: Session per request
│   ├── error_handler.py        # NEW: JSON error responses
│   └── logging.py              # NEW: Request/response logging
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── auth.py             # NEW: Login, register
│       ├── organisations.py    # NEW: Organisation endpoints
│       ├── users.py            # NEW: User endpoints
│       ├── cases.py            # NEW: Case endpoints
│       ├── documents.py        # NEW: Document endpoints
│       ├── upload_sessions.py  # NEW: Upload session endpoints
│       ├── draft_sessions.py   # NEW: Draft session endpoints
│       └── rulebooks.py        # NEW: Rulebook endpoints
├── schemas/
│   ├── __init__.py
│   ├── auth.py                 # NEW: Login, register schemas
│   ├── organisation.py         # NEW: Organisation schemas
│   ├── user.py                 # NEW: User schemas
│   ├── case.py                 # NEW: Case schemas
│   ├── document.py             # NEW: Document schemas
│   ├── upload_session.py       # NEW: Upload session schemas
│   ├── draft_session.py        # NEW: Draft session schemas
│   └── rulebook.py             # NEW: Rulebook schemas
├── dependencies.py             # NEW: Dependency injection (auth, db)
├── persistence/
│   ├── __init__.py
│   ├── models.py               # Phase 1 models
│   └── repositories.py         # Phase 1 repositories
└── workers/
    ├── __init__.py
    ├── document_processing.py  # NEW (stubs): OCR, embedding jobs
    ├── draft_research.py       # NEW (stubs): RAG search jobs
    └── draft_generation.py     # NEW (stubs): LLM drafting jobs
```

---

## Detailed Implementation Guide

### Step 1: Set Up FastAPI Application (Day 1)

**File: `src/app/main.py`**

```python
"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import (
    auth,
    organisations,
    users,
    cases,
    documents,
    upload_sessions,
    draft_sessions,
    rulebooks,
)
from app.middleware.database import DatabaseMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging import LoggingMiddleware

# Create FastAPI app
app = FastAPI(
    title="Junior Counsel API",
    description="Legal document processing and drafting system for South African litigation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:3000"] for Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters: last added runs first)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(DatabaseMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(organisations.router, prefix="/api/v1/organisations", tags=["Organisations"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(upload_sessions.router, prefix="/api/v1/upload-sessions", tags=["Upload Sessions"])
app.include_router(draft_sessions.router, prefix="/api/v1/draft-sessions", tags=["Draft Sessions"])
app.include_router(rulebooks.router, prefix="/api/v1/rulebooks", tags=["Rulebooks"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
    )
```

**File: `src/app/core/config.py` (Update)**

```python
"""
Application configuration using Pydantic BaseSettings.
"""
from typing import Optional
from pydantic import BaseSettings, PostgresDsn

class Settings(BaseSettings):
    # Database
    DATABASE_URL: PostgresDsn
    TEST_DATABASE_URL: Optional[PostgresDsn] = None

    # Security
    SECRET_KEY: str  # For JWT signing (use secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Redis (Phase 2.4)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Environment
    ENV: str = "development"  # development, test, production

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**File: `.env` (Create)**

```bash
# Database
DATABASE_URL=postgresql://localhost/junior_counsel
TEST_DATABASE_URL=postgresql://localhost/jc_test

# Security (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-secret-key-here-generate-with-secrets-module

# Environment
ENV=development

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

### Step 2: Implement Database Middleware (Day 1)

**File: `src/app/middleware/database.py`**

```python
"""
Database session middleware.

Provides a database session per request via request.state.db.
Automatically commits on success, rolls back on exception.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.core.db import SessionLocal

class DatabaseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Create a database session for each request."""
        # Create session
        db = SessionLocal()
        request.state.db = db

        try:
            response = await call_next(request)
            # Commit on successful response (2xx status codes)
            if 200 <= response.status_code < 300:
                db.commit()
            return response
        except Exception:
            # Rollback on exception
            db.rollback()
            raise
        finally:
            # Always close session
            db.close()
```

**File: `src/app/core/db.py` (Update from Phase 1)**

```python
"""
Database session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Create engine
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base for models (already defined in Phase 1)
Base = declarative_base()

def get_db():
    """
    Dependency for getting database session in route handlers.

    Usage:
        @router.get("/items")
        async def list_items(db: Session = Depends(get_db)):
            # db is available here
            pass
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

### Step 3: Implement Error Handling Middleware (Day 1)

**File: `src/app/middleware/error_handler.py`**

```python
"""
Error handling middleware for consistent JSON error responses.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import IntegrityError, NoResultFound
import logging

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except NoResultFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Resource not found",
                    "code": 404,
                },
            )
        except IntegrityError as e:
            logger.error(f"Database integrity error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Database constraint violation",
                    "code": 400,
                    "details": {"message": str(e.orig)},
                },
            )
        except ValueError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid value",
                    "code": 400,
                    "details": {"message": str(e)},
                },
            )
        except Exception as e:
            logger.exception(f"Unhandled exception: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "code": 500,
                    "details": {"message": "An unexpected error occurred"},
                },
            )
```

---

### Step 4: Implement Authentication (Days 2-3)

**File: `src/app/core/security.py`**

```python
"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode (should include 'sub' for user ID)
        expires_delta: Token expiration time (default: 30 minutes)

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Returns:
        Decoded payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

**File: `src/app/dependencies.py`**

```python
"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.persistence.models import User, OrganisationUser, OrganisationRoleEnum

# HTTP Bearer token scheme (for JWT)
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the currently authenticated user from JWT token.

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user

async def require_organisation_access(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganisationUser:
    """
    Verify that the current user has access to the specified organisation.

    Returns:
        OrganisationUser record with user's role

    Raises:
        HTTPException: 403 if user does not belong to organisation
    """
    org_user = db.query(OrganisationUser).filter(
        OrganisationUser.organisation_id == organisation_id,
        OrganisationUser.user_id == current_user.id,
    ).first()

    if org_user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organisation",
        )

    return org_user

async def require_admin_role(
    organisation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganisationUser:
    """
    Verify that the current user is an admin of the specified organisation.

    Raises:
        HTTPException: 403 if user is not an admin
    """
    org_user = await require_organisation_access(organisation_id, current_user, db)

    if org_user.role != OrganisationRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation",
        )

    return org_user
```

---

### Step 5: Implement Auth Endpoints (Day 3)

**File: `src/app/schemas/auth.py`**

```python
"""
Pydantic schemas for authentication endpoints.
"""
from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: int
    email: str
    full_name: str
    created_at: str

    class Config:
        from_attributes = True  # Pydantic V2 (was orm_mode in V1)
```

**File: `src/app/schemas/user.py`**

```python
"""
Pydantic schemas for user endpoints.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str

class UserUpdate(BaseModel):
    """Schema for updating a user."""
    full_name: str | None = None

class UserResponse(UserBase):
    """Schema for user in responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**File: `src/app/api/v1/auth.py`**

```python
"""
Authentication endpoints (register, login).
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.persistence.models import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **password**: Plain text password (will be hashed)
    - **full_name**: User's full name
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user (Note: User model needs password_hash field - add in Phase 1 models)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=hashed_password,  # Add this field to User model
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password to receive a JWT token.

    - **email**: User's email address
    - **password**: User's password

    Returns an access token valid for 30 minutes.
    """
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
```

---

## Testing Strategy

### Integration Tests (Phase 2.5)

**File: `tests/integration/test_auth.py`**

```python
"""
Integration tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, test_user):
    """Test user login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "error" in response.json()
```

---

## Success Criteria

### Phase 2 Definition of Done

- [ ] FastAPI application running on port 8000
- [ ] All 27 REST endpoints implemented
- [ ] JWT authentication working
- [ ] Role-based authorization enforced
- [ ] Organisation scoping validated (no cross-org access)
- [ ] File upload working for documents
- [ ] Pagination working on all list endpoints
- [ ] Redis/RQ integration for async operations
- [ ] 202 Accepted returned for async operations (per NFR-7a)
- [ ] Swagger docs accessible at /docs
- [ ] Integration tests ≥80% coverage
- [ ] All tests passing
- [ ] Error responses standardized (JSON format)
- [ ] CORS configured for frontend
- [ ] Code formatted with Black
- [ ] Type checking with mypy passes

---

## Next Steps After Phase 2

**Phase 3: Worker Implementation and RAG Pipeline**
- Implement DocumentProcessingJob (OCR, chunking, embedding)
- Implement DraftResearchJob (RAG search, case profiling)
- Implement DraftGenerationJob (LLM drafting with citations)
- Enable pgvector and implement vector similarity search
- Implement event-driven notifications (SSE or WebSocket)

See `documentation/Development_Plan.md` for complete Phase 3 details.

---

**Document Version**: 1.0
**Created**: 2026-03-11
**Status**: Ready for Implementation
