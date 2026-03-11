"""
Unit tests for SQLAlchemy models.

Tests basic CRUD operations, relationships, and model constraints.
"""
import pytest
from datetime import datetime

from app.persistence.models import (
    Organisation,
    User,
    OrganisationUser,
    OrganisationRoleEnum,
    Case,
    CaseStatusEnum,
)


@pytest.mark.unit
class TestOrganisation:
    """Test Organisation model."""

    def test_create_organisation(self, db_session):
        """Test creating a new organisation."""
        org = Organisation(
            name="Test Law Firm",
            contact_email="info@testfirm.co.za",
            is_active=True
        )
        db_session.add(org)
        db_session.flush()

        assert org.id is not None
        assert org.name == "Test Law Firm"
        assert org.contact_email == "info@testfirm.co.za"
        assert org.is_active is True
        assert isinstance(org.created_at, datetime)

    def test_organisation_unique_name(self, db_session):
        """Test that organisation names must be unique."""
        org1 = Organisation(name="Unique Firm")
        org2 = Organisation(name="Unique Firm")

        db_session.add(org1)
        db_session.flush()

        db_session.add(org2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.flush()


@pytest.mark.unit
class TestUser:
    """Test User model."""

    def test_create_user(self, db_session):
        """Test creating a new user."""
        user = User(
            email="advocate@example.com",
            full_name="John Advocate"
        )
        db_session.add(user)
        db_session.flush()

        assert user.id is not None
        assert user.email == "advocate@example.com"
        assert user.full_name == "John Advocate"
        assert isinstance(user.created_at, datetime)

    def test_user_unique_email(self, db_session):
        """Test that user emails must be unique."""
        user1 = User(email="same@example.com", full_name="User One")
        user2 = User(email="same@example.com", full_name="User Two")

        db_session.add(user1)
        db_session.flush()

        db_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.flush()


@pytest.mark.unit
class TestOrganisationUser:
    """Test OrganisationUser join model."""

    def test_create_organisation_user(self, db_session, organisation_factory, user_factory):
        """Test linking a user to an organisation with a role."""
        org = organisation_factory(name="Test Chambers")
        user = user_factory(email="advocate@chambers.co.za")

        org_user = OrganisationUser(
            organisation_id=org.id,
            user_id=user.id,
            role=OrganisationRoleEnum.PRACTITIONER
        )
        db_session.add(org_user)
        db_session.flush()

        assert org_user.id is not None
        assert org_user.organisation_id == org.id
        assert org_user.user_id == user.id
        assert org_user.role == OrganisationRoleEnum.PRACTITIONER

    def test_organisation_user_unique_constraint(self, db_session, organisation_factory, user_factory):
        """Test that a user cannot be added to the same organisation twice."""
        org = organisation_factory()
        user = user_factory()

        org_user1 = OrganisationUser(
            organisation_id=org.id,
            user_id=user.id,
            role=OrganisationRoleEnum.ADMIN
        )
        db_session.add(org_user1)
        db_session.flush()

        org_user2 = OrganisationUser(
            organisation_id=org.id,
            user_id=user.id,
            role=OrganisationRoleEnum.PRACTITIONER
        )
        db_session.add(org_user2)
        with pytest.raises(Exception):  # IntegrityError on unique constraint
            db_session.flush()


@pytest.mark.unit
class TestCase:
    """Test Case model."""

    def test_create_case(self, db_session, case_factory):
        """Test creating a new case."""
        case = case_factory(
            title="Smith v Jones",
            case_type="civil",
            jurisdiction="Gauteng High Court"
        )

        assert case.id is not None
        assert case.title == "Smith v Jones"
        assert case.case_type == "civil"
        assert case.jurisdiction == "Gauteng High Court"
        assert case.status == CaseStatusEnum.ACTIVE
        assert isinstance(case.created_at, datetime)

    def test_case_organisation_relationship(self, db_session, case_factory, organisation_factory):
        """Test that cases are linked to organisations."""
        org = organisation_factory(name="Legal Practice Inc")
        case = case_factory(title="Test Case", organisation=org)

        assert case.organisation_id == org.id
        assert case.organisation.name == "Legal Practice Inc"

    def test_case_owner_relationship(self, db_session, case_factory, user_factory):
        """Test that cases can have an owner."""
        user = user_factory(email="owner@example.com", full_name="Case Owner")
        case = case_factory(title="Owned Case", owner=user)

        assert case.owner_id == user.id
        assert case.owner.email == "owner@example.com"

    def test_case_metadata_json(self, db_session, case_factory):
        """Test that case metadata is stored as JSONB."""
        case = case_factory(title="Case with Metadata")
        case.metadata = {
            "court": "High Court",
            "case_number": "12345/2025",
            "parties": ["Plaintiff A", "Defendant B"]
        }
        db_session.flush()

        db_session.expire(case)  # Force reload from DB
        loaded_case = db_session.query(Case).filter_by(id=case.id).first()

        assert loaded_case.metadata["court"] == "High Court"
        assert loaded_case.metadata["case_number"] == "12345/2025"
        assert len(loaded_case.metadata["parties"]) == 2
