"""
Integration tests for DraftSession API endpoints (Phase 4.3).

Tests the REST API for draft session workflow:
1. POST /api/v1/draft-sessions - Create draft session
2. GET /api/v1/draft-sessions/{id} - Get draft session
3. GET /api/v1/draft-sessions - List draft sessions
4. PATCH /api/v1/draft-sessions/{id} - Update draft session
5. POST /api/v1/draft-sessions/{id}/answers - Submit intake responses
6. POST /api/v1/draft-sessions/{id}/start-generation - Trigger generation
7. GET /api/v1/draft-sessions/{id}/citations - Get citations
8. DELETE /api/v1/draft-sessions/{id} - Delete draft session
"""
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.persistence.models import (
    Organisation,
    User,
    Case,
    DraftSession,
    DraftSessionStatusEnum,
    Rulebook,
    RulebookStatusEnum
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_organisation(db_session: Session):
    """Create test organisation."""
    org = Organisation(
        name="Test Legal Chambers",
        contact_email="info@chambers.co.za",
        is_active=True
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session: Session):
    """Create test user."""
    from werkzeug.security import generate_password_hash

    user = User(
        email="advocate@chambers.co.za",
        password_hash=generate_password_hash("test_password"),
        full_name="Test Advocate"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_case(db_session: Session, test_organisation: Organisation, test_user: User):
    """Create test case."""
    case = Case(
        organisation_id=test_organisation.id,
        owner_id=test_user.id,
        title="Jones v Smith - Contract Dispute",
        description="Breach of employment contract case",
        case_type="civil",
        jurisdiction="High Court Gauteng"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def test_rulebook(db_session: Session, test_user: User):
    """Create test rulebook."""
    rulebook = Rulebook(
        document_type="affidavit",
        jurisdiction="High Court",
        version="1.0",
        label="High Court Affidavit Standard",
        status=RulebookStatusEnum.PUBLISHED,
        source_yaml="""
document_type: affidavit
jurisdiction: High Court
intake_questions:
  - field_id: deponent_name
    label: Deponent Full Name
    type: text
  - field_id: key_facts
    label: Key Facts
    type: textarea
structure:
  - name: Introduction
    description: Deponent identification
  - name: Facts
    description: Numbered factual paragraphs
""",
        rules_json={
            "document_type": "affidavit",
            "jurisdiction": "High Court",
            "intake_questions": [
                {"field_id": "deponent_name", "label": "Deponent Full Name", "type": "text"},
                {"field_id": "key_facts", "label": "Key Facts", "type": "textarea"}
            ],
            "structure": [
                {"name": "Introduction", "description": "Deponent identification"},
                {"name": "Facts", "description": "Numbered factual paragraphs"}
            ]
        },
        created_by_id=test_user.id
    )
    db_session.add(rulebook)
    db_session.commit()
    db_session.refresh(rulebook)
    return rulebook


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers (mock)."""
    # In real implementation, this would use JWT or session token
    # For now, we'll patch get_current_user dependency
    return {"Authorization": f"Bearer mock_token_{test_user.id}"}


@pytest.fixture
def mock_auth(test_user: User):
    """Mock authentication dependency."""
    def override_get_current_user():
        return test_user

    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield

    app.dependency_overrides.clear()


class TestDraftSessionCRUD:
    """Test basic CRUD operations for draft sessions."""

    def test_create_draft_session(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions - Create new draft session."""
        response = client.post(
            "/api/v1/draft-sessions/",
            json={
                "case_id": str(test_case.id),
                "rulebook_id": test_rulebook.id,
                "title": "Affidavit in Support",
                "document_type": "affidavit"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["case_id"] == str(test_case.id)
        assert data["rulebook_id"] == test_rulebook.id
        assert data["title"] == "Affidavit in Support"
        assert data["document_type"] == "affidavit"
        assert data["status"] == DraftSessionStatusEnum.INITIALIZING
        assert "id" in data
        assert "created_at" in data

    def test_get_draft_session(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions/{id} - Get draft session."""
        # Create draft session
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Test Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.AWAITING_INTAKE
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        # Get draft session
        response = client.get(f"/api/v1/draft-sessions/{draft.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(draft.id)
        assert data["title"] == "Test Draft"
        assert data["status"] == DraftSessionStatusEnum.AWAITING_INTAKE

    def test_get_draft_session_not_found(self, client: TestClient, mock_auth):
        """Test GET /api/v1/draft-sessions/{id} - 404 if not found."""
        import uuid
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/draft-sessions/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_draft_sessions(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions - List with pagination."""
        # Create multiple draft sessions
        for i in range(5):
            draft = DraftSession(
                case_id=test_case.id,
                user_id=test_user.id,
                rulebook_id=test_rulebook.id,
                title=f"Draft {i+1}",
                document_type="affidavit",
                status=DraftSessionStatusEnum.AWAITING_INTAKE
            )
            db_session.add(draft)
        db_session.commit()

        # List drafts for case
        response = client.get(
            "/api/v1/draft-sessions",
            params={"case_id": str(test_case.id), "page": 1, "per_page": 3}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["per_page"] == 3
        assert data["total"] == 5
        assert len(data["data"]) == 3
        assert data["next_page"] == 2

    def test_list_draft_sessions_filter_by_status(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions - Filter by status."""
        # Create drafts with different statuses
        draft1 = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft 1",
            document_type="affidavit",
            status=DraftSessionStatusEnum.AWAITING_INTAKE
        )
        draft2 = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft 2",
            document_type="affidavit",
            status=DraftSessionStatusEnum.REVIEW
        )
        db_session.add_all([draft1, draft2])
        db_session.commit()

        # Filter by status
        response = client.get(
            "/api/v1/draft-sessions",
            params={
                "case_id": str(test_case.id),
                "status": DraftSessionStatusEnum.REVIEW
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["data"][0]["status"] == DraftSessionStatusEnum.REVIEW

    def test_update_draft_session(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test PATCH /api/v1/draft-sessions/{id} - Update draft."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Original Title",
            document_type="affidavit",
            status=DraftSessionStatusEnum.INITIALIZING
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        # Update title only
        response = client.patch(
            f"/api/v1/draft-sessions/{draft.id}",
            json={"title": "Updated Title"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Updated Title"
        assert data["status"] == DraftSessionStatusEnum.INITIALIZING  # Unchanged

    def test_delete_draft_session(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test DELETE /api/v1/draft-sessions/{id} - Delete draft."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="To Delete",
            document_type="affidavit"
        )
        db_session.add(draft)
        db_session.commit()
        draft_id = draft.id

        # Delete draft
        response = client.delete(f"/api/v1/draft-sessions/{draft_id}")

        assert response.status_code == 204

        # Verify deleted
        deleted = db_session.get(DraftSession, draft_id)
        assert deleted is None


class TestDraftSessionWorkflow:
    """Test draft session workflow endpoints (Phase 4.3)."""

    def test_submit_intake_responses(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions/{id}/answers - Submit intake."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft Affidavit",
            document_type="affidavit",
            status=DraftSessionStatusEnum.INITIALIZING
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        # Submit intake responses
        intake_data = {
            "deponent_name": "John Smith",
            "key_facts": "I am the applicant. The contract was breached."
        }

        response = client.post(
            f"/api/v1/draft-sessions/{draft.id}/answers",
            json={"intake_responses": intake_data}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == DraftSessionStatusEnum.AWAITING_INTAKE
        assert data["intake_responses"] == intake_data

    def test_submit_intake_responses_invalid_status(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions/{id}/answers - Reject if wrong status."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.REVIEW  # Already generated
        )
        db_session.add(draft)
        db_session.commit()

        response = client.post(
            f"/api/v1/draft-sessions/{draft.id}/answers",
            json={"intake_responses": {"key": "value"}}
        )

        assert response.status_code == 400
        assert "Cannot submit intake" in response.json()["detail"]

    def test_start_draft_generation(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions/{id}/start-generation - Enqueue jobs."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.AWAITING_INTAKE,
            intake_responses={"deponent_name": "John Smith"}
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        # Mock queue enqueue
        with patch('app.core.queue.enqueue_draft_research') as mock_enqueue:
            mock_enqueue.return_value = "job_123"

            response = client.post(f"/api/v1/draft-sessions/{draft.id}/start-generation")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == DraftSessionStatusEnum.RESEARCH
        mock_enqueue.assert_called_once_with(str(draft.id))

    def test_start_generation_missing_intake(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions/{id}/start-generation - Reject if no intake."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.AWAITING_INTAKE,
            intake_responses=None  # Missing
        )
        db_session.add(draft)
        db_session.commit()

        response = client.post(f"/api/v1/draft-sessions/{draft.id}/start-generation")

        assert response.status_code == 400
        assert "Intake responses required" in response.json()["detail"]

    def test_start_generation_wrong_status(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test POST /api/v1/draft-sessions/{id}/start-generation - Reject if wrong status."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.RESEARCH,  # Already in progress
            intake_responses={"key": "value"}
        )
        db_session.add(draft)
        db_session.commit()

        response = client.post(f"/api/v1/draft-sessions/{draft.id}/start-generation")

        assert response.status_code == 400
        assert "Cannot start generation" in response.json()["detail"]

    def test_get_draft_citations(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions/{id}/citations - Get citations."""
        import uuid

        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.REVIEW,
            draft_doc={
                "content": "Generated content [1] with citations [2].",
                "citations": [
                    {
                        "marker": "[1]",
                        "content": "Employment contract excerpt",
                        "document": "contract.pdf",
                        "document_id": str(uuid.uuid4()),
                        "page": 1,
                        "similarity": 0.92
                    },
                    {
                        "marker": "[2]",
                        "content": "Termination clause excerpt",
                        "document": "contract.pdf",
                        "document_id": str(uuid.uuid4()),
                        "page": 2,
                        "similarity": 0.88
                    }
                ]
            }
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        response = client.get(f"/api/v1/draft-sessions/{draft.id}/citations")

        assert response.status_code == 200
        data = response.json()

        assert data["draft_session_id"] == str(draft.id)
        assert data["total_citations"] == 2
        assert len(data["citations"]) == 2

        # Verify citation structure
        citation1 = data["citations"][0]
        assert citation1["marker"] == "[1]"
        assert citation1["content"] == "Employment contract excerpt"
        assert citation1["document_name"] == "contract.pdf"
        assert citation1["page"] == 1
        assert citation1["similarity"] == 0.92

    def test_get_citations_not_ready(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions/{id}/citations - Reject if not generated."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.RESEARCH  # Not yet generated
        )
        db_session.add(draft)
        db_session.commit()

        response = client.get(f"/api/v1/draft-sessions/{draft.id}/citations")

        assert response.status_code == 400
        assert "Citations not available" in response.json()["detail"]

    def test_get_citations_empty(
        self,
        client: TestClient,
        db_session: Session,
        test_case: Case,
        test_user: User,
        test_rulebook: Rulebook,
        mock_auth
    ):
        """Test GET /api/v1/draft-sessions/{id}/citations - Handle no citations."""
        draft = DraftSession(
            case_id=test_case.id,
            user_id=test_user.id,
            rulebook_id=test_rulebook.id,
            title="Draft",
            document_type="affidavit",
            status=DraftSessionStatusEnum.REVIEW,
            draft_doc={"content": "No citations"}  # No citations key
        )
        db_session.add(draft)
        db_session.commit()

        response = client.get(f"/api/v1/draft-sessions/{draft.id}/citations")

        assert response.status_code == 200
        data = response.json()

        assert data["total_citations"] == 0
        assert len(data["citations"]) == 0


class TestDraftSessionAuthentication:
    """Test authentication requirements for draft session endpoints."""

    def test_create_draft_requires_auth(self, client: TestClient):
        """Test POST /api/v1/draft-sessions - Reject without auth."""
        response = client.post(
            "/api/v1/draft-sessions/",
            json={"case_id": "fake", "rulebook_id": 1, "title": "Test", "document_type": "affidavit"}
        )

        assert response.status_code == 401

    def test_get_draft_requires_auth(self, client: TestClient):
        """Test GET /api/v1/draft-sessions/{id} - Reject without auth."""
        import uuid
        response = client.get(f"/api/v1/draft-sessions/{uuid.uuid4()}")

        assert response.status_code == 401

    def test_list_drafts_requires_auth(self, client: TestClient):
        """Test GET /api/v1/draft-sessions - Reject without auth."""
        import uuid
        response = client.get("/api/v1/draft-sessions", params={"case_id": str(uuid.uuid4())})

        assert response.status_code == 401
