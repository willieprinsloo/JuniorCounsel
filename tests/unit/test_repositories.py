"""
Unit tests for repository classes.

Tests CRUD operations, filtering, pagination, and business logic in repositories.
"""
import pytest
from datetime import datetime

# NOTE: Repository classes will be implemented in src/app/persistence/repositories.py
# These tests are written test-first to guide implementation


@pytest.mark.unit
class TestCaseRepository:
    """Test CaseRepository."""

    @pytest.fixture
    def case_repository(self, db_session):
        """Provide a CaseRepository instance."""
        from app.persistence.repositories import CaseRepository
        return CaseRepository(db_session)

    def test_create_case(self, case_repository, organisation_factory, user_factory):
        """Test creating a new case via repository."""
        org = organisation_factory()
        user = user_factory()

        case = case_repository.create(
            organisation_id=org.id,
            owner_id=user.id,
            title="New Case",
            case_type="civil",
            jurisdiction="South Africa"
        )

        assert case.id is not None
        assert case.title == "New Case"
        assert case.organisation_id == org.id
        assert case.owner_id == user.id

    def test_get_by_id(self, case_repository, case_factory):
        """Test retrieving a case by ID."""
        created_case = case_factory(title="Test Case")

        retrieved_case = case_repository.get_by_id(created_case.id)

        assert retrieved_case is not None
        assert retrieved_case.id == created_case.id
        assert retrieved_case.title == "Test Case"

    def test_get_by_id_not_found(self, case_repository):
        """Test that get_by_id returns None for non-existent ID."""
        import uuid
        non_existent_id = uuid.uuid4()

        case = case_repository.get_by_id(non_existent_id)

        assert case is None

    def test_list_by_organisation(self, case_repository, case_factory, organisation_factory):
        """Test listing cases filtered by organisation."""
        org1 = organisation_factory(name="Org 1")
        org2 = organisation_factory(name="Org 2")

        case_factory(title="Case 1", organisation=org1)
        case_factory(title="Case 2", organisation=org1)
        case_factory(title="Case 3", organisation=org2)

        org1_cases, total = case_repository.list(organisation_id=org1.id)

        assert len(org1_cases) == 2
        assert total == 2
        assert all(c.organisation_id == org1.id for c in org1_cases)

    def test_list_with_pagination(self, case_repository, case_factory, organisation_factory):
        """Test pagination in list queries."""
        org = organisation_factory()

        # Create 25 cases
        for i in range(25):
            case_factory(title=f"Case {i}", organisation=org)

        # Get first page (20 per page default)
        page1, total = case_repository.list(
            organisation_id=org.id,
            page=1,
            per_page=10
        )

        assert len(page1) == 10
        assert total == 25

        # Get second page
        page2, total = case_repository.list(
            organisation_id=org.id,
            page=2,
            per_page=10
        )

        assert len(page2) == 10
        # Ensure different cases on different pages
        page1_ids = {c.id for c in page1}
        page2_ids = {c.id for c in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_with_status_filter(self, case_repository, case_factory, organisation_factory):
        """Test filtering cases by status."""
        from app.persistence.models import CaseStatusEnum

        org = organisation_factory()
        case_factory(title="Active 1", organisation=org, status=CaseStatusEnum.ACTIVE)
        case_factory(title="Active 2", organisation=org, status=CaseStatusEnum.ACTIVE)
        case_factory(title="Closed 1", organisation=org, status=CaseStatusEnum.CLOSED)

        active_cases, total = case_repository.list(
            organisation_id=org.id,
            status=CaseStatusEnum.ACTIVE
        )

        assert len(active_cases) == 2
        assert total == 2
        assert all(c.status == CaseStatusEnum.ACTIVE for c in active_cases)

    def test_search_by_title(self, case_repository, case_factory, organisation_factory):
        """Test case-insensitive search by title."""
        org = organisation_factory()
        case_factory(title="Smith v Jones", organisation=org)
        case_factory(title="Brown v Green", organisation=org)
        case_factory(title="Jones v Smith", organisation=org)

        # Search for "jones" (case-insensitive)
        results, total = case_repository.list(
            organisation_id=org.id,
            q="jones"
        )

        assert len(results) == 2
        assert all("jones" in c.title.lower() for c in results)

    def test_update_case_status(self, case_repository, case_factory):
        """Test updating case status."""
        from app.persistence.models import CaseStatusEnum

        case = case_factory(status=CaseStatusEnum.ACTIVE)
        original_updated_at = case.updated_at

        updated_case = case_repository.update_status(case.id, CaseStatusEnum.CLOSED)

        assert updated_case.status == CaseStatusEnum.CLOSED
        assert updated_case.updated_at > original_updated_at

    def test_delete_case(self, case_repository, case_factory):
        """Test soft or hard delete of a case."""
        case = case_factory(title="To Delete")

        deleted = case_repository.delete(case.id)

        assert deleted is True
        assert case_repository.get_by_id(case.id) is None


@pytest.mark.unit
class TestOrganisationRepository:
    """Test OrganisationRepository."""

    @pytest.fixture
    def org_repository(self, db_session):
        """Provide an OrganisationRepository instance."""
        from app.persistence.repositories import OrganisationRepository
        return OrganisationRepository(db_session)

    def test_create_organisation(self, org_repository):
        """Test creating a new organisation."""
        org = org_repository.create(
            name="Test Law Firm",
            contact_email="info@testfirm.co.za"
        )

        assert org.id is not None
        assert org.name == "Test Law Firm"
        assert org.is_active is True

    def test_get_by_id(self, org_repository, organisation_factory):
        """Test retrieving organisation by ID."""
        created_org = organisation_factory(name="My Firm")

        retrieved_org = org_repository.get_by_id(created_org.id)

        assert retrieved_org is not None
        assert retrieved_org.id == created_org.id
        assert retrieved_org.name == "My Firm"

    def test_list_active_organisations(self, org_repository, organisation_factory):
        """Test listing only active organisations."""
        organisation_factory(name="Active Org", is_active=True)
        organisation_factory(name="Inactive Org", is_active=False)

        active_orgs = org_repository.list_active()

        assert len(active_orgs) == 1
        assert active_orgs[0].name == "Active Org"

    def test_add_user_to_organisation(self, org_repository, organisation_factory, user_factory):
        """Test adding a user to an organisation with a role."""
        from app.persistence.models import OrganisationRoleEnum

        org = organisation_factory()
        user = user_factory()

        org_user = org_repository.add_user(
            organisation_id=org.id,
            user_id=user.id,
            role=OrganisationRoleEnum.PRACTITIONER
        )

        assert org_user.organisation_id == org.id
        assert org_user.user_id == user.id
        assert org_user.role == OrganisationRoleEnum.PRACTITIONER

    def test_remove_user_from_organisation(self, org_repository, organisation_factory, user_factory):
        """Test removing a user from an organisation."""
        from app.persistence.models import OrganisationRoleEnum, OrganisationUser

        org = organisation_factory()
        user = user_factory()

        # Add user first
        org_repository.add_user(org.id, user.id, OrganisationRoleEnum.STAFF)

        # Remove user
        removed = org_repository.remove_user(org.id, user.id)

        assert removed is True
        # Verify user is no longer in organisation


@pytest.mark.unit
class TestUploadSessionRepository:
    """Test UploadSessionRepository."""

    @pytest.fixture
    def upload_session_repository(self, db_session):
        """Provide an UploadSessionRepository instance."""
        from app.persistence.repositories import UploadSessionRepository
        return UploadSessionRepository(db_session)

    def test_create_upload_session(self, upload_session_repository, case_factory, user_factory):
        """Test creating a new upload session."""
        case = case_factory()
        user = user_factory()

        session = upload_session_repository.create(
            case_id=str(case.id),
            uploaded_by_id=user.id,
            total_documents=5,
        )

        assert session.id is not None
        assert str(session.case_id) == str(case.id)
        assert session.uploaded_by_id == user.id
        assert session.total_documents == 5
        assert session.completed_documents == 0
        assert session.failed_documents == 0

    def test_update_counts(self, upload_session_repository, case_factory, user_factory, db_session):
        """Test updating document counts."""
        from app.persistence.models import UploadSession

        case = case_factory()
        user = user_factory()

        session = UploadSession(
            case_id=case.id,
            uploaded_by_id=user.id,
            total_documents=10,
        )
        db_session.add(session)
        db_session.flush()

        updated = upload_session_repository.update_counts(
            upload_session_id=str(session.id),
            completed_increment=3,
            failed_increment=1,
        )

        assert updated is not None
        assert updated.completed_documents == 3
        assert updated.failed_documents == 1


# TODO: Add tests for DraftSessionRepository, RulebookRepository when needed
