"""
Pytest configuration and shared fixtures for Junior Counsel tests.
"""
import os
import pytest
from contextlib import contextmanager

# Set test environment before importing app modules
os.environ["ENV"] = "test"
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/jc_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql://localhost/jc_test")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.db import Base, get_session
from app.core.config import settings


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine for the session."""
    test_db_url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    _engine = create_engine(str(test_db_url), pool_pre_ping=True)

    # Create all tables
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)

    yield _engine

    # Cleanup
    Base.metadata.drop_all(_engine)
    _engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """
    Provide a database session for a test.

    Each test gets a fresh session with automatic rollback.
    This ensures test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client():
    """
    Provide a test client for API testing.

    TODO: Implement when Flask/FastAPI app is created.
    """
    # from app import create_app
    # app = create_app()
    # app.config['TESTING'] = True
    # return app.test_client()
    pytest.skip("API client not yet implemented")


@pytest.fixture
def auth_headers():
    """
    Provide authentication headers for API testing.

    TODO: Implement when authentication is added.
    """
    # return {"Authorization": "Bearer test_token"}
    pytest.skip("Authentication not yet implemented")


# Fixture factories for common test data

@pytest.fixture
def organisation_factory(db_session):
    """Factory for creating test organisations."""
    from app.persistence.models import Organisation

    def _create_organisation(name="Test Org", contact_email="test@example.com", is_active=True):
        org = Organisation(
            name=name,
            contact_email=contact_email,
            is_active=is_active
        )
        db_session.add(org)
        db_session.flush()
        return org

    return _create_organisation


@pytest.fixture
def user_factory(db_session):
    """Factory for creating test users."""
    from app.persistence.models import User
    import uuid

    def _create_user(email=None, full_name="Test User", password_hash="$2b$12$placeholder_hash"):
        # Generate unique email if not provided
        if email is None:
            email = f"user-{uuid.uuid4().hex[:8]}@example.com"

        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _create_user


@pytest.fixture
def case_factory(db_session, organisation_factory, user_factory):
    """Factory for creating test cases."""
    from app.persistence.models import Case, CaseStatusEnum

    def _create_case(
        title="Test Case",
        organisation=None,
        owner=None,
        case_type="civil",
        status=CaseStatusEnum.ACTIVE,
        jurisdiction="South Africa"
    ):
        if organisation is None:
            organisation = organisation_factory()
        if owner is None:
            owner = user_factory()

        case = Case(
            organisation_id=organisation.id,
            owner_id=owner.id,
            title=title,
            case_type=case_type,
            status=status,
            jurisdiction=jurisdiction
        )
        db_session.add(case)
        db_session.flush()
        return case

    return _create_case


# Mock AI providers for testing

class MockEmbeddingProvider:
    """Mock embedding provider that returns fixed vectors."""

    def embed_text(self, text: str) -> list[float]:
        """Return a fixed 1536-dimensional vector."""
        return [0.1] * 1536

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return fixed vectors for a batch of texts."""
        return [[0.1] * 1536 for _ in texts]


class MockLLMProvider:
    """Mock LLM provider that returns fixed responses."""

    def __init__(self, response: str = "Mock LLM response"):
        self.response = response
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        """Return a fixed response."""
        self.call_count += 1
        return self.response


@pytest.fixture
def mock_embedding_provider():
    """Provide a mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
def mock_llm_provider():
    """Provide a mock LLM provider."""
    return MockLLMProvider()


# Markers for test organization

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, external dependencies)"
    )
    config.addinivalue_line(
        "markers", "worker: Worker and background job tests"
    )
    config.addinivalue_line(
        "markers", "security: Security and authentication tests"
    )
