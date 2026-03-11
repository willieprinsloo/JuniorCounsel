"""
Rulebook YAML validation.

Validates rulebook YAML against expected schema for:
- intake_questions structure
- document_structure sections
- validation_rules format
- citation_rules
"""
import yaml
from typing import Optional


class RulebookValidationError(Exception):
    """Raised when rulebook YAML is invalid."""
    pass


class RulebookValidator:
    """
    Validates rulebook YAML structure.

    Expected schema:
    ```yaml
    intake_questions:
      - name: field_name
        label: "User-facing label"
        type: text|textarea|select|date
        required: true|false
        options: [...]  # For select type
        help_text: "..."

    document_structure:
      - section_name: "Introduction"
        order: 1
        required: true
        subsections: [...]

    validation_rules:
      - rule_name: "has_deponent_signature"
        type: required_field
        target: deponent_signature
        error_message: "..."

    citation_rules:
      format: endnotes|inline
      style: bluebook|oscola
    ```
    """

    @staticmethod
    def validate(yaml_content: str) -> dict:
        """
        Validate rulebook YAML and return parsed structure.

        Args:
            yaml_content: YAML string to validate

        Returns:
            Parsed YAML as dict

        Raises:
            RulebookValidationError: If YAML is invalid
        """
        # Step 1: Parse YAML
        try:
            parsed = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise RulebookValidationError(f"YAML syntax error: {str(e)}")

        if not isinstance(parsed, dict):
            raise RulebookValidationError("Root element must be a dictionary")

        errors = []

        # Step 2: Validate intake_questions
        if "intake_questions" in parsed:
            try:
                RulebookValidator._validate_intake_questions(parsed["intake_questions"])
            except RulebookValidationError as e:
                errors.append(str(e))

        # Step 3: Validate document_structure
        if "document_structure" in parsed:
            try:
                RulebookValidator._validate_document_structure(parsed["document_structure"])
            except RulebookValidationError as e:
                errors.append(str(e))

        # Step 4: Validate validation_rules
        if "validation_rules" in parsed:
            try:
                RulebookValidator._validate_validation_rules(parsed["validation_rules"])
            except RulebookValidationError as e:
                errors.append(str(e))

        # Step 5: Validate citation_rules
        if "citation_rules" in parsed:
            try:
                RulebookValidator._validate_citation_rules(parsed["citation_rules"])
            except RulebookValidationError as e:
                errors.append(str(e))

        if errors:
            raise RulebookValidationError(f"Validation errors: {'; '.join(errors)}")

        return parsed

    @staticmethod
    def _validate_intake_questions(questions):
        """Validate intake_questions structure."""
        if not isinstance(questions, list):
            raise RulebookValidationError("intake_questions must be a list")

        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                raise RulebookValidationError(f"intake_questions[{i}] must be a dict")

            # Required fields
            if "name" not in q:
                raise RulebookValidationError(f"intake_questions[{i}] missing 'name' field")
            if "label" not in q:
                raise RulebookValidationError(f"intake_questions[{i}] missing 'label' field")
            if "type" not in q:
                raise RulebookValidationError(f"intake_questions[{i}] missing 'type' field")

            # Validate type
            valid_types = ["text", "textarea", "select", "date", "checkbox", "number"]
            if q["type"] not in valid_types:
                raise RulebookValidationError(
                    f"intake_questions[{i}].type must be one of {valid_types}"
                )

            # If type is select, must have options
            if q["type"] == "select" and "options" not in q:
                raise RulebookValidationError(
                    f"intake_questions[{i}] of type 'select' must have 'options'"
                )

    @staticmethod
    def _validate_document_structure(structure):
        """Validate document_structure."""
        if not isinstance(structure, list):
            raise RulebookValidationError("document_structure must be a list")

        for i, section in enumerate(structure):
            if not isinstance(section, dict):
                raise RulebookValidationError(f"document_structure[{i}] must be a dict")

            if "section_name" not in section:
                raise RulebookValidationError(f"document_structure[{i}] missing 'section_name'")

    @staticmethod
    def _validate_validation_rules(rules):
        """Validate validation_rules."""
        if not isinstance(rules, list):
            raise RulebookValidationError("validation_rules must be a list")

        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise RulebookValidationError(f"validation_rules[{i}] must be a dict")

            if "rule_name" not in rule:
                raise RulebookValidationError(f"validation_rules[{i}] missing 'rule_name'")
            if "type" not in rule:
                raise RulebookValidationError(f"validation_rules[{i}] missing 'type'")

    @staticmethod
    def _validate_citation_rules(rules):
        """Validate citation_rules."""
        if not isinstance(rules, dict):
            raise RulebookValidationError("citation_rules must be a dict")

        if "format" in rules:
            valid_formats = ["endnotes", "inline", "footnotes"]
            if rules["format"] not in valid_formats:
                raise RulebookValidationError(
                    f"citation_rules.format must be one of {valid_formats}"
                )


# Example valid rulebook YAML
EXAMPLE_RULEBOOK_YAML = """
intake_questions:
  - name: deponent_name
    label: "Full Name of Deponent"
    type: text
    required: true
    help_text: "Enter the full legal name of the person making the affidavit"

  - name: capacity
    label: "Capacity"
    type: select
    required: true
    options:
      - Plaintiff
      - Defendant
      - Witness
      - Expert

  - name: facts
    label: "Statement of Facts"
    type: textarea
    required: true
    help_text: "List the key facts in chronological order"

document_structure:
  - section_name: "Introduction"
    order: 1
    required: true
    description: "Deponent identification and capacity"

  - section_name: "Facts"
    order: 2
    required: true
    description: "Chronological statement of facts"

  - section_name: "Conclusion"
    order: 3
    required: true
    description: "Confirmation and signature"

validation_rules:
  - rule_name: "has_deponent_signature"
    type: required_field
    target: deponent_signature
    error_message: "Affidavit must be signed by deponent"

citation_rules:
  format: endnotes
  style: bluebook
"""
