"""
Rulebook service for parsing, validating, and managing rulebooks.

This service handles:
- Parsing YAML rulebooks into validated JSON
- Version selection (latest published rulebook)
- Publishing/deprecating rulebooks
- Template variable substitution in research queries

Phase 4.1 implementation - FR-38 to FR-43.
"""
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import yaml
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.persistence.models import Rulebook, RulebookStatusEnum
from app.persistence.repositories import RulebookRepository
from app.schemas.rulebook_schema import RulebookSchema


logger = logging.getLogger(__name__)


class RulebookValidationError(Exception):
    """Raised when rulebook YAML validation fails."""
    pass


class RulebookService:
    """Service for managing rulebooks."""

    def __init__(self, db_session: Session):
        """
        Initialize rulebook service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.repo = RulebookRepository(db_session)

    def parse_yaml(self, source_yaml: str) -> Dict[str, Any]:
        """
        Parse YAML string to validated rules_json.

        Args:
            source_yaml: Raw YAML string from Rulebook.source_yaml

        Returns:
            Validated rules_json dict

        Raises:
            RulebookValidationError: If YAML is invalid or fails schema validation
        """
        try:
            # Parse YAML
            yaml_data = yaml.safe_load(source_yaml)
            if not yaml_data:
                raise RulebookValidationError("Empty YAML content")

            # Validate against Pydantic schema
            rulebook_schema = RulebookSchema(**yaml_data)

            # Convert to dict (rules_json)
            rules_json = rulebook_schema.model_dump()

            logger.info(f"Successfully parsed rulebook: {rules_json['metadata']['label']}")
            return rules_json

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise RulebookValidationError(f"Invalid YAML syntax: {str(e)}")

        except ValidationError as e:
            logger.error(f"Rulebook validation error: {e}")
            # Format Pydantic errors for user-friendly display
            error_messages = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error['loc'])
                error_messages.append(f"{field_path}: {error['msg']}")

            raise RulebookValidationError(
                f"Rulebook validation failed:\n" + "\n".join(error_messages)
            )

        except Exception as e:
            logger.error(f"Unexpected error parsing rulebook: {e}", exc_info=True)
            raise RulebookValidationError(f"Failed to parse rulebook: {str(e)}")

    def validate_rules(self, rules_json: Dict[str, Any]) -> bool:
        """
        Validate rules_json against Pydantic schema.

        Args:
            rules_json: Parsed rules JSON

        Returns:
            True if valid

        Raises:
            RulebookValidationError: If validation fails
        """
        try:
            RulebookSchema(**rules_json)
            return True
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error['loc'])
                error_messages.append(f"{field_path}: {error['msg']}")

            raise RulebookValidationError(
                f"Rules JSON validation failed:\n" + "\n".join(error_messages)
            )

    def compute_content_hash(self, source_yaml: str) -> str:
        """
        Compute SHA-256 hash of source YAML.

        This hash is used to detect if a rulebook has been modified.

        Args:
            source_yaml: Raw YAML string

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(source_yaml.encode('utf-8')).hexdigest()

    def get_latest_published(
        self,
        document_type: str,
        jurisdiction: str
    ) -> Optional[Rulebook]:
        """
        Get the latest published rulebook for a document type and jurisdiction.

        Args:
            document_type: Document type (e.g., "affidavit", "pleading")
            jurisdiction: Jurisdiction (e.g., "south_africa_high_court")

        Returns:
            Latest published Rulebook or None if not found
        """
        stmt = select(Rulebook).where(
            and_(
                Rulebook.document_type == document_type,
                Rulebook.jurisdiction == jurisdiction,
                Rulebook.status == RulebookStatusEnum.PUBLISHED
            )
        ).order_by(Rulebook.created_at.desc())

        result = self.db.execute(stmt).scalars().first()
        return result

    def publish_rulebook(self, rulebook_id: int) -> Rulebook:
        """
        Publish a draft rulebook, making it available for new DraftSessions.

        Args:
            rulebook_id: Rulebook ID to publish

        Returns:
            Updated Rulebook

        Raises:
            ValueError: If rulebook is not in draft status or validation fails
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if rulebook.status != RulebookStatusEnum.DRAFT:
            raise ValueError(
                f"Only draft rulebooks can be published. "
                f"Current status: {rulebook.status}"
            )

        # Validate rules_json before publishing
        if not rulebook.rules_json:
            raise ValueError("Cannot publish rulebook without validated rules_json")

        try:
            self.validate_rules(rulebook.rules_json)
        except RulebookValidationError as e:
            raise ValueError(f"Cannot publish invalid rulebook: {str(e)}")

        # Update status to published
        rulebook.status = RulebookStatusEnum.PUBLISHED
        rulebook.updated_at = datetime.utcnow()
        self.db.flush()

        logger.info(
            f"Published rulebook {rulebook_id}: "
            f"{rulebook.document_type} v{rulebook.version}"
        )
        return rulebook

    def deprecate_rulebook(self, rulebook_id: int) -> Rulebook:
        """
        Deprecate a published rulebook.

        Deprecated rulebooks cannot be used for new DraftSessions but existing
        drafts using this version are unaffected.

        Args:
            rulebook_id: Rulebook ID to deprecate

        Returns:
            Updated Rulebook

        Raises:
            ValueError: If rulebook is not published
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if rulebook.status != RulebookStatusEnum.PUBLISHED:
            raise ValueError(
                f"Only published rulebooks can be deprecated. "
                f"Current status: {rulebook.status}"
            )

        # Update status to deprecated
        rulebook.status = RulebookStatusEnum.DEPRECATED
        rulebook.updated_at = datetime.utcnow()
        self.db.flush()

        logger.info(
            f"Deprecated rulebook {rulebook_id}: "
            f"{rulebook.document_type} v{rulebook.version}"
        )
        return rulebook

    def create_from_yaml(
        self,
        source_yaml: str,
        created_by_id: int,
        auto_publish: bool = False
    ) -> Rulebook:
        """
        Create a new rulebook from YAML source.

        Args:
            source_yaml: Raw YAML string
            created_by_id: User ID creating the rulebook
            auto_publish: If True, publish immediately after validation

        Returns:
            Created Rulebook

        Raises:
            RulebookValidationError: If YAML validation fails
        """
        # Parse and validate YAML
        rules_json = self.parse_yaml(source_yaml)

        # Extract metadata
        metadata = rules_json['metadata']
        document_type = metadata['document_type']
        jurisdiction = metadata['jurisdiction']
        version = metadata['version']
        label = metadata.get('label', f"{document_type} v{version}")

        # Compute content hash
        content_hash = self.compute_content_hash(source_yaml)

        # Create rulebook
        rulebook = Rulebook(
            document_type=document_type,
            jurisdiction=jurisdiction,
            version=version,
            label=label,
            source_yaml=source_yaml,
            rules_json=rules_json,
            content_hash=content_hash,
            status=RulebookStatusEnum.DRAFT,
            created_by_id=created_by_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(rulebook)
        self.db.flush()

        logger.info(f"Created rulebook {rulebook.id}: {label}")

        # Auto-publish if requested
        if auto_publish:
            self.publish_rulebook(rulebook.id)

        return rulebook

    def update_from_yaml(
        self,
        rulebook_id: int,
        source_yaml: str
    ) -> Rulebook:
        """
        Update an existing rulebook from YAML source.

        Only draft rulebooks can be updated. Published rulebooks must be
        duplicated to a new version.

        Args:
            rulebook_id: Rulebook ID to update
            source_yaml: New YAML source

        Returns:
            Updated Rulebook

        Raises:
            ValueError: If rulebook is not in draft status
            RulebookValidationError: If YAML validation fails
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if rulebook.status != RulebookStatusEnum.DRAFT:
            raise ValueError(
                f"Only draft rulebooks can be updated. "
                f"Current status: {rulebook.status}. "
                f"To modify a published rulebook, duplicate it to a new version."
            )

        # Parse and validate new YAML
        rules_json = self.parse_yaml(source_yaml)

        # Update rulebook
        rulebook.source_yaml = source_yaml
        rulebook.rules_json = rules_json
        rulebook.content_hash = self.compute_content_hash(source_yaml)
        rulebook.updated_at = datetime.utcnow()
        self.db.flush()

        logger.info(f"Updated rulebook {rulebook_id}")
        return rulebook

    def duplicate_rulebook(
        self,
        source_rulebook_id: int,
        new_version: str,
        created_by_id: int
    ) -> Rulebook:
        """
        Duplicate an existing rulebook to a new version.

        This is the recommended way to create a new version of a published rulebook.

        Args:
            source_rulebook_id: Rulebook ID to duplicate
            new_version: Version string for the new rulebook
            created_by_id: User ID creating the duplicate

        Returns:
            New Rulebook (status=DRAFT)

        Raises:
            ValueError: If source rulebook not found or version already exists
        """
        source = self.repo.get_by_id(source_rulebook_id)
        if not source:
            raise ValueError(f"Source rulebook {source_rulebook_id} not found")

        # Check if version already exists
        existing = self.db.execute(
            select(Rulebook).where(
                and_(
                    Rulebook.document_type == source.document_type,
                    Rulebook.jurisdiction == source.jurisdiction,
                    Rulebook.version == new_version
                )
            )
        ).scalars().first()

        if existing:
            raise ValueError(
                f"Rulebook version {new_version} already exists for "
                f"{source.document_type} in {source.jurisdiction}"
            )

        # Create duplicate with new version
        new_rulebook = Rulebook(
            document_type=source.document_type,
            jurisdiction=source.jurisdiction,
            version=new_version,
            label=f"{source.document_type} v{new_version}",
            source_yaml=source.source_yaml,
            rules_json=source.rules_json,
            content_hash=source.content_hash,
            status=RulebookStatusEnum.DRAFT,
            created_by_id=created_by_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(new_rulebook)
        self.db.flush()

        logger.info(
            f"Duplicated rulebook {source_rulebook_id} to {new_rulebook.id} "
            f"(version {new_version})"
        )
        return new_rulebook

    def substitute_template_variables(
        self,
        template: str,
        intake_answers: Dict[str, Any]
    ) -> str:
        """
        Substitute {placeholders} in templates with intake answers.

        Used for research query templates and content templates.

        Args:
            template: Template string with {field_id} placeholders
            intake_answers: Dict of intake answers (field_id -> value)

        Returns:
            String with placeholders replaced

        Example:
            >>> template = "What are the facts about {relief_sought}?"
            >>> answers = {"relief_sought": "payment of debt"}
            >>> substitute_template_variables(template, answers)
            "What are the facts about payment of debt?"
        """
        try:
            return template.format(**intake_answers)
        except KeyError as e:
            logger.warning(f"Template variable {e} not found in intake answers")
            # Return template with unfilled placeholders rather than failing
            return template

    def get_intake_questions(self, rulebook_id: int) -> List[Dict[str, Any]]:
        """
        Get intake questions from a rulebook.

        Args:
            rulebook_id: Rulebook ID

        Returns:
            List of intake question dicts

        Raises:
            ValueError: If rulebook not found or rules_json invalid
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if not rulebook.rules_json:
            raise ValueError(f"Rulebook {rulebook_id} has no rules_json")

        return rulebook.rules_json.get('intake_questions', [])

    def get_document_structure(self, rulebook_id: int) -> List[Dict[str, Any]]:
        """
        Get document structure from a rulebook.

        Args:
            rulebook_id: Rulebook ID

        Returns:
            List of document section dicts

        Raises:
            ValueError: If rulebook not found or rules_json invalid
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if not rulebook.rules_json:
            raise ValueError(f"Rulebook {rulebook_id} has no rules_json")

        return rulebook.rules_json.get('document_structure', [])

    def get_research_queries(
        self,
        rulebook_id: int,
        intake_answers: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Get research query templates with optional variable substitution.

        Args:
            rulebook_id: Rulebook ID
            intake_answers: Optional dict of intake answers for template substitution

        Returns:
            List of research query strings

        Raises:
            ValueError: If rulebook not found or rules_json invalid
        """
        rulebook = self.repo.get_by_id(rulebook_id)
        if not rulebook:
            raise ValueError(f"Rulebook {rulebook_id} not found")

        if not rulebook.rules_json:
            raise ValueError(f"Rulebook {rulebook_id} has no rules_json")

        query_templates = rulebook.rules_json.get('research_query_templates', [])
        queries = []

        for template_obj in query_templates:
            template = template_obj['template']

            # Substitute variables if intake answers provided
            if intake_answers:
                query = self.substitute_template_variables(template, intake_answers)
            else:
                query = template

            queries.append(query)

        return queries
