"""
Pydantic schemas for Rulebook YAML validation.

This module defines the complete structure for rulebook YAML files that control
court document drafting workflows. Rulebooks specify:
- Intake questions for gathering case facts
- Document structure (sections, headings, templates)
- Validation rules for completeness checking
- Research query templates for RAG
- Drafting prompts and style guidance

Phase 4.1 implementation - FR-38 to FR-43.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Intake Question Schema
# ============================================================================

class IntakeQuestion(BaseModel):
    """
    A single intake question for gathering case information from the user.

    Example:
        ```yaml
        - id: case_number
          question: "What is the case number?"
          field_type: text
          required: true
          help_text: "Enter the court case number (e.g., 12345/2024)"
        ```
    """
    id: str = Field(
        ...,
        description="Unique identifier for this question (used in answers dict)",
        min_length=1,
        max_length=64,
        pattern=r'^[a-z0-9_]+$'  # Snake_case IDs only
    )
    question: str = Field(
        ...,
        description="The question text displayed to the user",
        min_length=5,
        max_length=500
    )
    field_type: Literal["text", "textarea", "select", "date", "number", "boolean"] = Field(
        ...,
        description="Input field type for the UI"
    )
    required: bool = Field(
        default=True,
        description="Whether this question must be answered before generation"
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="Options for select field type (required if field_type=select)"
    )
    default_value: Optional[str] = Field(
        default=None,
        description="Default value pre-filled in the form"
    )
    validation: Optional[str] = Field(
        default=None,
        description="Validation rule (e.g., regex pattern, min/max length)",
        max_length=200
    )
    help_text: Optional[str] = Field(
        default=None,
        description="Help text shown below the question",
        max_length=500
    )
    conditional_on: Optional[str] = Field(
        default=None,
        description="Show this question only if another question's answer matches",
        max_length=100
    )

    @field_validator('options')
    @classmethod
    def validate_select_options(cls, v, info):
        """Ensure options are provided for select field type."""
        field_type = info.data.get('field_type')
        if field_type == 'select' and not v:
            raise ValueError("Options must be provided for select field type")
        if field_type != 'select' and v:
            raise ValueError(f"Options not allowed for field_type={field_type}")
        return v


# ============================================================================
# Document Structure Schema
# ============================================================================

class DocumentSection(BaseModel):
    """
    A section in the generated document (e.g., heading, paragraph, sub-section).

    Example:
        ```yaml
        - section_id: introduction
          title: "INTRODUCTION"
          content_template: "This is an affidavit in support of..."
          required: true
          subsections: []
        ```
    """
    section_id: str = Field(
        ...,
        description="Unique identifier for this section",
        min_length=1,
        max_length=64,
        pattern=r'^[a-z0-9_]+$'
    )
    title: str = Field(
        ...,
        description="Section heading text (displayed in document)",
        min_length=1,
        max_length=200
    )
    content_template: Optional[str] = Field(
        default=None,
        description="Optional template text for LLM guidance (not shown verbatim)",
        max_length=2000
    )
    required: bool = Field(
        default=True,
        description="Whether this section must be present in the final draft"
    )
    minimum_paragraphs: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Minimum number of paragraphs required in this section"
    )
    maximum_paragraphs: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum number of paragraphs allowed in this section"
    )
    prompt_guidance: Optional[str] = Field(
        default=None,
        description="Specific instructions for LLM when drafting this section",
        max_length=1000
    )
    subsections: Optional[List["DocumentSection"]] = Field(
        default=None,
        description="Nested sub-sections (hierarchical structure)"
    )

    @model_validator(mode='after')
    def validate_paragraph_range(self):
        """Ensure minimum <= maximum if both specified."""
        if (self.minimum_paragraphs is not None and
            self.maximum_paragraphs is not None and
            self.minimum_paragraphs > self.maximum_paragraphs):
            raise ValueError(
                f"minimum_paragraphs ({self.minimum_paragraphs}) cannot exceed "
                f"maximum_paragraphs ({self.maximum_paragraphs})"
            )
        return self


# ============================================================================
# Validation Rule Schema
# ============================================================================

class ValidationRule(BaseModel):
    """
    A validation rule for completeness checking before finalisation.

    Example:
        ```yaml
        - rule_id: has_all_sections
          description: "All required sections must be present"
          rule_type: section_presence
          parameters:
            required_sections: [introduction, facts, relief]
        ```
    """
    rule_id: str = Field(
        ...,
        description="Unique identifier for this validation rule",
        min_length=1,
        max_length=64,
        pattern=r'^[a-z0-9_]+$'
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this rule checks",
        min_length=10,
        max_length=500
    )
    rule_type: Literal[
        "section_presence",      # Check required sections exist
        "minimum_length",        # Check section/document length
        "citation_count",        # Check minimum citations present
        "intake_field_used",     # Check intake answer is referenced
        "custom_regex"           # Custom regex validation
    ] = Field(
        ...,
        description="Type of validation to perform"
    )
    parameters: Dict[str, Any] = Field(
        ...,
        description="Parameters specific to the rule_type"
    )
    severity: Literal["error", "warning"] = Field(
        default="error",
        description="Whether violation blocks finalisation (error) or just warns (warning)"
    )


# ============================================================================
# Research Query Template Schema
# ============================================================================

class ResearchQueryTemplate(BaseModel):
    """
    A template for generating RAG search queries during draft research.

    Example:
        ```yaml
        - query_id: find_facts
          template: "What are the material facts in {case_type}?"
          description: "Searches for factual allegations in case documents"
        ```
    """
    query_id: str = Field(
        ...,
        description="Unique identifier for this query template",
        min_length=1,
        max_length=64,
        pattern=r'^[a-z0-9_]+$'
    )
    template: str = Field(
        ...,
        description="Query template with {placeholders} for intake answers",
        min_length=5,
        max_length=500
    )
    description: Optional[str] = Field(
        default=None,
        description="Explanation of what this query searches for",
        max_length=500
    )
    similarity_threshold: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieved chunks"
    )
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of chunks to retrieve for this query"
    )


# ============================================================================
# Drafting Prompt Schema
# ============================================================================

class DraftingPrompt(BaseModel):
    """
    Configuration for LLM prompting during document generation.

    Example:
        ```yaml
        system_message: "You are an expert South African litigation attorney..."
        temperature: 0.5
        max_tokens: 4000
        style_guidance: "Use formal legal language appropriate for High Court..."
        ```
    """
    system_message: str = Field(
        ...,
        description="System message defining LLM persona and expertise",
        min_length=20,
        max_length=2000
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0=deterministic, 2=creative)"
    )
    max_tokens: int = Field(
        default=4000,
        ge=500,
        le=32000,
        description="Maximum tokens in generated response"
    )
    style_guidance: Optional[str] = Field(
        default=None,
        description="Specific style instructions (tone, formality, conventions)",
        max_length=2000
    )
    citation_format: Literal["numbered", "inline", "footnotes"] = Field(
        default="numbered",
        description="Citation format to use ([1], [2] vs inline vs footnotes)"
    )
    south_african_conventions: bool = Field(
        default=True,
        description="Apply South African legal formatting conventions"
    )


# ============================================================================
# Complete Rulebook Schema
# ============================================================================

class RulebookSchema(BaseModel):
    """
    Complete rulebook schema for a document type.

    This is the top-level schema that validates the entire YAML file.
    When parsed and validated, it becomes the `rules_json` field in the
    Rulebook database model.

    Example YAML:
        ```yaml
        metadata:
          document_type: "affidavit"
          jurisdiction: "south_africa_high_court"
          version: "1.0.0"
          label: "Founding Affidavit (High Court)"

        intake_questions:
          - id: deponent_name
            question: "Full name of deponent"
            field_type: text
            required: true

        document_structure:
          - section_id: introduction
            title: "INTRODUCTION"
            required: true

        validation_rules:
          - rule_id: has_all_sections
            description: "All required sections present"
            rule_type: section_presence
            parameters:
              required_sections: [introduction, facts, relief]

        research_query_templates:
          - query_id: find_facts
            template: "What are the key facts in this matter?"

        drafting_prompt:
          system_message: "You are an expert South African advocate..."
          temperature: 0.5
          max_tokens: 4000
        ```
    """

    # Metadata
    metadata: Dict[str, str] = Field(
        ...,
        description="Rulebook metadata (document_type, jurisdiction, version, label)"
    )

    # Intake questions
    intake_questions: List[IntakeQuestion] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Questions to gather case information from user"
    )

    # Document structure
    document_structure: List[DocumentSection] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Hierarchical structure of the document (sections, headings)"
    )

    # Validation rules
    validation_rules: Optional[List[ValidationRule]] = Field(
        default=None,
        max_length=50,
        description="Rules for validating completeness before finalisation"
    )

    # Research queries
    research_query_templates: Optional[List[ResearchQueryTemplate]] = Field(
        default=None,
        max_length=20,
        description="Query templates for RAG research phase"
    )

    # Drafting prompt configuration
    drafting_prompt: DraftingPrompt = Field(
        ...,
        description="LLM prompting configuration for document generation"
    )

    # Optional custom fields
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom fields for future extensibility"
    )

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v):
        """Ensure required metadata fields are present."""
        required_fields = ['document_type', 'jurisdiction', 'version', 'label']
        missing = [f for f in required_fields if f not in v]
        if missing:
            raise ValueError(f"Missing required metadata fields: {', '.join(missing)}")
        return v

    @field_validator('intake_questions')
    @classmethod
    def validate_unique_question_ids(cls, v):
        """Ensure all question IDs are unique."""
        ids = [q.id for q in v]
        duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
        if duplicates:
            raise ValueError(f"Duplicate question IDs found: {', '.join(set(duplicates))}")
        return v

    @field_validator('document_structure')
    @classmethod
    def validate_unique_section_ids(cls, v):
        """Ensure all section IDs are unique (including nested sections)."""
        def collect_ids(sections, ids=None):
            if ids is None:
                ids = []
            for section in sections:
                ids.append(section.section_id)
                if section.subsections:
                    collect_ids(section.subsections, ids)
            return ids

        ids = collect_ids(v)
        duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
        if duplicates:
            raise ValueError(f"Duplicate section IDs found: {', '.join(set(duplicates))}")
        return v

    @field_validator('research_query_templates')
    @classmethod
    def validate_unique_query_ids(cls, v):
        """Ensure all query IDs are unique."""
        if v is None:
            return v
        ids = [q.query_id for q in v]
        duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
        if duplicates:
            raise ValueError(f"Duplicate query IDs found: {', '.join(set(duplicates))}")
        return v


# ============================================================================
# Export model for documentation and JSON Schema generation
# ============================================================================

# Update forward references for recursive models
DocumentSection.model_rebuild()


# Example usage:
# ```python
# from app.schemas.rulebook_schema import RulebookSchema
# import yaml
#
# # Load YAML
# with open('affidavit_rulebook.yaml') as f:
#     yaml_data = yaml.safe_load(f)
#
# # Validate
# try:
#     rulebook = RulebookSchema(**yaml_data)
#     print(f"✅ Rulebook valid: {rulebook.metadata['label']}")
#     rules_json = rulebook.model_dump()
# except ValidationError as e:
#     print(f"❌ Validation errors:\n{e}")
# ```
