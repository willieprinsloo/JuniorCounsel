"""
Unit tests for Rulebook service (Phase 4.1).

Tests:
- YAML parsing and validation
- Version selection
- Publishing/deprecating rulebooks
- Template variable substitution
- Error handling
"""
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.rulebook import RulebookService, RulebookValidationError
from app.persistence.models import Rulebook, RulebookStatusEnum, User
from app.persistence.repositories import RulebookRepository


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def rulebook_service(db_session: Session) -> RulebookService:
    """Create RulebookService instance."""
    return RulebookService(db_session)


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="fake_hash",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def affidavit_yaml() -> str:
    """Load affidavit rulebook YAML fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "rulebooks" / "affidavit_founding.yaml"
    return fixture_path.read_text()


@pytest.fixture
def pleading_yaml() -> str:
    """Load pleading rulebook YAML fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "rulebooks" / "pleading_particulars_of_claim.yaml"
    return fixture_path.read_text()


@pytest.fixture
def invalid_yaml() -> str:
    """Invalid YAML (syntax error)."""
    return """
metadata:
  document_type: "affidavit"
  jurisdiction: "south_africa"
  [invalid syntax here
"""


@pytest.fixture
def missing_required_fields_yaml() -> str:
    """Valid YAML but missing required Pydantic fields."""
    return """
metadata:
  document_type: "affidavit"
  # Missing jurisdiction, version, label

intake_questions:
  - id: deponent_name
    question: "Full name"
    field_type: text
    required: true

document_structure:
  - section_id: intro
    title: "Introduction"
    required: true

drafting_prompt:
  system_message: "You are an expert attorney"
  temperature: 0.5
  max_tokens: 4000
"""


# ============================================================================
# Test YAML Parsing
# ============================================================================

def test_parse_valid_affidavit_yaml(rulebook_service: RulebookService, affidavit_yaml: str):
    """Test parsing valid affidavit YAML."""
    rules_json = rulebook_service.parse_yaml(affidavit_yaml)

    assert rules_json is not None
    assert 'metadata' in rules_json
    assert rules_json['metadata']['document_type'] == 'affidavit'
    assert rules_json['metadata']['jurisdiction'] == 'south_africa_high_court'
    assert rules_json['metadata']['version'] == '1.0.0'
    assert 'intake_questions' in rules_json
    assert 'document_structure' in rules_json
    assert 'drafting_prompt' in rules_json


def test_parse_valid_pleading_yaml(rulebook_service: RulebookService, pleading_yaml: str):
    """Test parsing valid pleading YAML."""
    rules_json = rulebook_service.parse_yaml(pleading_yaml)

    assert rules_json is not None
    assert rules_json['metadata']['document_type'] == 'pleading'
    assert len(rules_json['intake_questions']) > 0
    assert len(rules_json['document_structure']) > 0


def test_parse_invalid_yaml_syntax(rulebook_service: RulebookService, invalid_yaml: str):
    """Test parsing YAML with syntax errors."""
    with pytest.raises(RulebookValidationError) as exc_info:
        rulebook_service.parse_yaml(invalid_yaml)

    assert "Invalid YAML syntax" in str(exc_info.value)


def test_parse_missing_required_fields(
    rulebook_service: RulebookService,
    missing_required_fields_yaml: str
):
    """Test parsing YAML with missing required Pydantic fields."""
    with pytest.raises(RulebookValidationError) as exc_info:
        rulebook_service.parse_yaml(missing_required_fields_yaml)

    error_message = str(exc_info.value)
    assert "validation failed" in error_message.lower()
    # Should mention missing metadata fields
    assert "jurisdiction" in error_message or "version" in error_message


def test_parse_empty_yaml(rulebook_service: RulebookService):
    """Test parsing empty YAML."""
    with pytest.raises(RulebookValidationError) as exc_info:
        rulebook_service.parse_yaml("")

    assert "Empty YAML content" in str(exc_info.value)


# ============================================================================
# Test Validation
# ============================================================================

def test_validate_rules_success(
    rulebook_service: RulebookService,
    affidavit_yaml: str
):
    """Test validating correct rules_json."""
    rules_json = rulebook_service.parse_yaml(affidavit_yaml)
    assert rulebook_service.validate_rules(rules_json) is True


def test_validate_rules_invalid(rulebook_service: RulebookService):
    """Test validating invalid rules_json."""
    invalid_rules = {
        "metadata": {"document_type": "affidavit"},  # Missing required fields
        # Missing intake_questions, document_structure, drafting_prompt
    }

    with pytest.raises(RulebookValidationError):
        rulebook_service.validate_rules(invalid_rules)


# ============================================================================
# Test Content Hash
# ============================================================================

def test_compute_content_hash(rulebook_service: RulebookService):
    """Test SHA-256 hash computation."""
    yaml1 = "key: value"
    yaml2 = "key: value"
    yaml3 = "key: different"

    hash1 = rulebook_service.compute_content_hash(yaml1)
    hash2 = rulebook_service.compute_content_hash(yaml2)
    hash3 = rulebook_service.compute_content_hash(yaml3)

    # Same content = same hash
    assert hash1 == hash2
    # Different content = different hash
    assert hash1 != hash3
    # Hash is 64 hex characters (SHA-256)
    assert len(hash1) == 64


# ============================================================================
# Test Get Latest Published
# ============================================================================

def test_get_latest_published_single(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting latest published rulebook."""
    # Create and publish a rulebook
    rulebook = rulebook_service.create_from_yaml(
        affidavit_yaml,
        test_user.id,
        auto_publish=True
    )

    # Get latest published
    latest = rulebook_service.get_latest_published(
        "affidavit",
        "south_africa_high_court"
    )

    assert latest is not None
    assert latest.id == rulebook.id
    assert latest.status == RulebookStatusEnum.PUBLISHED


def test_get_latest_published_multiple_versions(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting latest when multiple versions exist."""
    # Create v1.0.0
    rb1 = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=True)

    # Create v2.0.0 (duplicate and publish)
    rb2 = rulebook_service.duplicate_rulebook(rb1.id, "2.0.0", test_user.id)
    rulebook_service.publish_rulebook(rb2.id)

    # Latest should be v2.0.0 (most recently created)
    latest = rulebook_service.get_latest_published("affidavit", "south_africa_high_court")

    assert latest is not None
    assert latest.id == rb2.id
    assert latest.version == "2.0.0"


def test_get_latest_published_not_found(rulebook_service: RulebookService):
    """Test getting latest published when none exists."""
    latest = rulebook_service.get_latest_published("nonexistent", "fake_jurisdiction")
    assert latest is None


def test_get_latest_published_only_draft(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting latest published when only draft exists."""
    # Create draft (not published)
    rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=False)

    # Should return None (no published version)
    latest = rulebook_service.get_latest_published("affidavit", "south_africa_high_court")
    assert latest is None


# ============================================================================
# Test Publishing
# ============================================================================

def test_publish_rulebook_success(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test publishing a draft rulebook."""
    # Create draft
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)
    assert rulebook.status == RulebookStatusEnum.DRAFT

    # Publish
    published = rulebook_service.publish_rulebook(rulebook.id)

    assert published.id == rulebook.id
    assert published.status == RulebookStatusEnum.PUBLISHED


def test_publish_already_published(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test publishing a rulebook that's already published."""
    # Create and publish
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=True)

    # Try to publish again
    with pytest.raises(ValueError) as exc_info:
        rulebook_service.publish_rulebook(rulebook.id)

    assert "Only draft rulebooks can be published" in str(exc_info.value)


def test_publish_nonexistent(rulebook_service: RulebookService):
    """Test publishing nonexistent rulebook."""
    with pytest.raises(ValueError) as exc_info:
        rulebook_service.publish_rulebook(99999)

    assert "not found" in str(exc_info.value)


# ============================================================================
# Test Deprecating
# ============================================================================

def test_deprecate_rulebook_success(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test deprecating a published rulebook."""
    # Create and publish
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=True)
    assert rulebook.status == RulebookStatusEnum.PUBLISHED

    # Deprecate
    deprecated = rulebook_service.deprecate_rulebook(rulebook.id)

    assert deprecated.id == rulebook.id
    assert deprecated.status == RulebookStatusEnum.DEPRECATED


def test_deprecate_draft(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test deprecating a draft rulebook (should fail)."""
    # Create draft
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    # Try to deprecate
    with pytest.raises(ValueError) as exc_info:
        rulebook_service.deprecate_rulebook(rulebook.id)

    assert "Only published rulebooks can be deprecated" in str(exc_info.value)


# ============================================================================
# Test Create from YAML
# ============================================================================

def test_create_from_yaml_success(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test creating rulebook from YAML."""
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    assert rulebook.id is not None
    assert rulebook.document_type == "affidavit"
    assert rulebook.jurisdiction == "south_africa_high_court"
    assert rulebook.version == "1.0.0"
    assert rulebook.status == RulebookStatusEnum.DRAFT
    assert rulebook.source_yaml == affidavit_yaml
    assert rulebook.rules_json is not None
    assert rulebook.content_hash is not None
    assert rulebook.created_by_id == test_user.id


def test_create_from_yaml_with_auto_publish(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test creating rulebook with auto-publish."""
    rulebook = rulebook_service.create_from_yaml(
        affidavit_yaml,
        test_user.id,
        auto_publish=True
    )

    assert rulebook.status == RulebookStatusEnum.PUBLISHED


def test_create_from_invalid_yaml(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    invalid_yaml: str
):
    """Test creating rulebook from invalid YAML."""
    with pytest.raises(RulebookValidationError):
        rulebook_service.create_from_yaml(invalid_yaml, test_user.id)


# ============================================================================
# Test Update from YAML
# ============================================================================

def test_update_from_yaml_success(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test updating draft rulebook from YAML."""
    # Create draft
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)
    original_hash = rulebook.content_hash

    # Modify YAML
    modified_yaml = affidavit_yaml.replace("version: \"1.0.0\"", "version: \"1.0.1\"")

    # Update
    updated = rulebook_service.update_from_yaml(rulebook.id, modified_yaml)

    assert updated.id == rulebook.id
    assert updated.source_yaml == modified_yaml
    assert updated.content_hash != original_hash
    assert updated.rules_json['metadata']['version'] == "1.0.1"


def test_update_published_rulebook_fails(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test updating published rulebook (should fail)."""
    # Create and publish
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=True)

    # Try to update
    with pytest.raises(ValueError) as exc_info:
        rulebook_service.update_from_yaml(rulebook.id, affidavit_yaml)

    assert "Only draft rulebooks can be updated" in str(exc_info.value)


# ============================================================================
# Test Duplicate Rulebook
# ============================================================================

def test_duplicate_rulebook_success(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test duplicating rulebook to new version."""
    # Create original
    original = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id, auto_publish=True)

    # Duplicate
    duplicate = rulebook_service.duplicate_rulebook(original.id, "2.0.0", test_user.id)

    assert duplicate.id != original.id
    assert duplicate.version == "2.0.0"
    assert duplicate.status == RulebookStatusEnum.DRAFT
    assert duplicate.document_type == original.document_type
    assert duplicate.jurisdiction == original.jurisdiction
    assert duplicate.source_yaml == original.source_yaml
    assert duplicate.content_hash == original.content_hash


def test_duplicate_to_existing_version_fails(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test duplicating to a version that already exists."""
    # Create original
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    # Try to duplicate to same version
    with pytest.raises(ValueError) as exc_info:
        rulebook_service.duplicate_rulebook(rulebook.id, "1.0.0", test_user.id)

    assert "already exists" in str(exc_info.value)


# ============================================================================
# Test Template Variable Substitution
# ============================================================================

def test_substitute_template_variables_success(rulebook_service: RulebookService):
    """Test substituting template variables."""
    template = "What are the facts about {relief_sought} in case {case_number}?"
    intake_answers = {
        "relief_sought": "payment of debt",
        "case_number": "12345/2024"
    }

    result = rulebook_service.substitute_template_variables(template, intake_answers)

    assert result == "What are the facts about payment of debt in case 12345/2024?"


def test_substitute_template_variables_missing_key(rulebook_service: RulebookService):
    """Test substituting with missing variable (should return template unchanged)."""
    template = "Find facts about {nonexistent_field}"
    intake_answers = {"other_field": "value"}

    result = rulebook_service.substitute_template_variables(template, intake_answers)

    # Should return template with unfilled placeholder
    assert "{nonexistent_field}" in result


# ============================================================================
# Test Get Intake Questions
# ============================================================================

def test_get_intake_questions(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting intake questions from rulebook."""
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    questions = rulebook_service.get_intake_questions(rulebook.id)

    assert len(questions) > 0
    assert questions[0]['id'] == 'deponent_name'
    assert questions[0]['question'] == "Full name of the deponent"
    assert questions[0]['field_type'] == 'text'
    assert questions[0]['required'] is True


# ============================================================================
# Test Get Document Structure
# ============================================================================

def test_get_document_structure(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting document structure from rulebook."""
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    structure = rulebook_service.get_document_structure(rulebook.id)

    assert len(structure) > 0
    assert structure[0]['section_id'] == 'introduction'
    assert structure[0]['title'] == "INTRODUCTION"
    assert structure[0]['required'] is True


# ============================================================================
# Test Get Research Queries
# ============================================================================

def test_get_research_queries_without_substitution(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting research queries without variable substitution."""
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    queries = rulebook_service.get_research_queries(rulebook.id)

    assert len(queries) > 0
    # Should contain templates with placeholders
    assert any("{" in q for q in queries if "{" in q)


def test_get_research_queries_with_substitution(
    db_session: Session,
    rulebook_service: RulebookService,
    test_user: User,
    affidavit_yaml: str
):
    """Test getting research queries with variable substitution."""
    rulebook = rulebook_service.create_from_yaml(affidavit_yaml, test_user.id)

    intake_answers = {"relief_sought": "payment of damages"}
    queries = rulebook_service.get_research_queries(rulebook.id, intake_answers)

    assert len(queries) > 0
    # Placeholders should be substituted
    assert "payment of damages" in " ".join(queries)
