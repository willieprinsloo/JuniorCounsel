"""
Draft session endpoints for document drafting workflow.
"""
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DraftSessionStatusEnum
from app.persistence.repositories import DraftSessionRepository, CitationRepository
from app.schemas.draft_session import (
    DraftSessionCreate,
    DraftSessionUpdate,
    DraftSessionResponse,
    DraftSessionListResponse,
    IntakeResponsesSubmit,
    CitationResponse,
    CitationsListResponse,
)
from app.services.draft_export import DraftExportService

router = APIRouter()


@router.post("/", response_model=DraftSessionResponse, status_code=status.HTTP_201_CREATED)
def create_draft_session(
    draft_data: DraftSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new draft session.

    Requires authentication.

    Args:
        draft_data: Draft session creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created draft session object (status: awaiting_intake)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.create(
        case_id=draft_data.case_id,
        user_id=current_user.id,
        rulebook_id=draft_data.rulebook_id,
        title=draft_data.title,
        document_type=draft_data.document_type
    )

    # Immediately transition to AWAITING_INTAKE (no initialization needed)
    # The frontend will either collect intake responses or start generation directly
    draft_session.status = DraftSessionStatusEnum.AWAITING_INTAKE
    db.flush()
    db.commit()  # CRITICAL: Commit immediately so subsequent operations can see it

    return draft_session


@router.get("/{draft_session_id}", response_model=DraftSessionResponse)
def get_draft_session(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a draft session by ID.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Draft session object

    Raises:
        HTTPException: If draft session not found (404)
    """
    import logging
    logger = logging.getLogger(__name__)

    draft_repo = DraftSessionRepository(db)
    logger.info(f"GET draft_session: Attempting to fetch draft with ID: {draft_session_id}")
    draft_session = draft_repo.get_by_id(draft_session_id)
    logger.info(f"GET draft_session: Result: {draft_session is not None}")

    if not draft_session:
        logger.warning(f"GET draft_session: Draft not found: {draft_session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    logger.info(f"GET draft_session: Returning draft: {draft_session.id}")
    return draft_session


@router.get("/", response_model=DraftSessionListResponse)
def list_draft_sessions(
    case_id: str = Query(..., description="Case ID to filter draft sessions"),
    status: Optional[DraftSessionStatusEnum] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List draft sessions with pagination and filtering.

    Requires authentication.

    Args:
        case_id: Case ID (required)
        status: Filter by draft status
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of draft sessions
    """
    draft_repo = DraftSessionRepository(db)
    drafts, total = draft_repo.list(
        case_id=case_id,
        status=status,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": drafts,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.patch("/{draft_session_id}", response_model=DraftSessionResponse)
def update_draft_session(
    draft_session_id: str,
    draft_data: DraftSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a draft session.

    Requires authentication. Only updates provided fields.

    Args:
        draft_session_id: Draft session ID (UUID)
        draft_data: Draft session update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft session object

    Raises:
        HTTPException: If draft session not found (404)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Update only provided fields
    if draft_data.title is not None:
        draft_session.title = draft_data.title
    if draft_data.intake_responses is not None:
        draft_session.intake_responses = draft_data.intake_responses
    if draft_data.status is not None:
        draft_session.status = draft_data.status

    db.flush()
    db.commit()
    return draft_session


@router.delete("/{draft_session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_session(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a draft session.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If draft session not found (404)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    db.delete(draft_session)
    db.flush()
    db.commit()


@router.get("/{draft_session_id}/intake-questions")
def get_intake_questions(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get intake questions for a draft session from its rulebook.

    Returns the intake questions from the rulebook's source YAML.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of intake questions with field, prompt, and required flag

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If rulebook not found (404)
    """
    import yaml
    from app.persistence.models import Rulebook

    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Get rulebook
    rulebook = db.query(Rulebook).filter(Rulebook.id == draft_session.rulebook_id).first()
    if not rulebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rulebook not found"
        )

    # Parse YAML to get intake questions
    try:
        yaml_data = yaml.safe_load(rulebook.source_yaml)
        raw_questions = yaml_data.get('intake_questions', [])

        # Normalize field names for frontend compatibility
        # Support both old format (field/prompt) and new format (id/question)
        normalized_questions = []
        for q in raw_questions:
            normalized_questions.append({
                "field": q.get('id') or q.get('field'),
                "prompt": q.get('question') or q.get('prompt'),
                "required": q.get('required', False),
                "type": q.get('field_type') or q.get('type', 'text'),
                "options": q.get('options'),
                "help_text": q.get('help_text'),
                "conditional_on": q.get('conditional_on'),
            })

        return {
            "draft_session_id": str(draft_session.id),
            "questions": normalized_questions
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse rulebook YAML: {str(e)}"
        )


@router.post("/{draft_session_id}/answers", response_model=DraftSessionResponse)
def submit_intake_responses(
    draft_session_id: str,
    intake_data: IntakeResponsesSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit intake responses for a draft session.

    Updates the draft session with user's answers to intake questions
    and transitions status to AWAITING_INTAKE → ready for generation.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        intake_data: Intake responses (dict of field_id → value)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft session object with intake_responses populated

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft session not in valid state for intake (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (should be INITIALIZING or AWAITING_INTAKE)
    if draft_session.status not in [
        DraftSessionStatusEnum.INITIALIZING,
        DraftSessionStatusEnum.AWAITING_INTAKE
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit intake for draft in {draft_session.status} status"
        )

    # Update intake responses
    draft_session.intake_responses = intake_data.intake_responses
    draft_session.status = DraftSessionStatusEnum.AWAITING_INTAKE

    db.flush()
    db.commit()  # Commit the transaction to persist changes
    return draft_session


@router.post("/{draft_session_id}/start-generation", response_model=DraftSessionResponse)
def start_draft_generation(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start draft generation for a draft session.

    Enqueues background jobs for research and draft generation.
    Transitions status to RESEARCH → background workers process.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Draft session object with updated status (RESEARCH)

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft session not ready for generation (400)
        HTTPException: If intake responses missing (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (should be AWAITING_INTAKE)
    if draft_session.status != DraftSessionStatusEnum.AWAITING_INTAKE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start generation for draft in {draft_session.status} status. "
                   f"Expected {DraftSessionStatusEnum.AWAITING_INTAKE}"
        )

    # Validate intake responses provided
    if not draft_session.intake_responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intake responses required before starting generation. "
                   "Submit answers first via POST /draft-sessions/{id}/answers"
        )

    # Update status FIRST, commit, THEN enqueue job
    # This ensures the worker can find the draft session in the database
    draft_session.status = DraftSessionStatusEnum.RESEARCH
    db.flush()
    db.commit()  # CRITICAL: Commit BEFORE enqueuing so worker can see the draft!

    # Now enqueue the job - worker will be able to find the committed draft session
    from app.core.queue import enqueue_draft_research

    try:
        job_id = enqueue_draft_research(draft_session_id)
        return draft_session

    except Exception as e:
        # If enqueueing fails, rollback the status change
        draft_session.status = DraftSessionStatusEnum.AWAITING_INTAKE
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue draft generation: {str(e)}"
        )


@router.put("/{draft_session_id}/content", response_model=DraftSessionResponse)
def update_draft_content(
    draft_session_id: str,
    content: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update draft content while in REVIEW status.

    Allows users to manually edit the generated draft content before finalizing.
    Only available when draft is in REVIEW or READY status.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        content: New draft content ({"content": "updated text"})
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft session object

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not in REVIEW/READY status (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (must be REVIEW or READY to edit)
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit draft in {draft_session.status} status. "
                   f"Draft must be in REVIEW or READY status to edit."
        )

    # Update draft content
    if not draft_session.draft_doc:
        draft_session.draft_doc = {}

    if "content" in content:
        draft_session.draft_doc["content"] = content["content"]
        draft_session.draft_doc["manually_edited"] = True
        draft_session.draft_doc["edited_at"] = __import__('datetime').datetime.utcnow().isoformat()

    db.flush()
    db.commit()

    return draft_session


@router.post("/{draft_session_id}/chat")
def chat_with_draft(
    draft_session_id: str,
    message: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with AI to improve/modify the draft with tool calling support.

    Uses GPT-5 with tool calling to:
    - Search case documents for relevant information
    - Retrieve citation details
    - Make targeted improvements to the draft
    - Maintain conversation history

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        message: Chat message ({"message": "add more details from exhibits", "history": [...]})
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated draft content, AI response, and tool usage information

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not in REVIEW status (400)
    """
    import json
    from app.core.ai_providers import LLMProvider
    from app.persistence.models import Case, DocumentChunk, Document
    from app.persistence.token_usage_repository import TokenUsageRepository
    from app.persistence.models import TokenUsageTypeEnum
    from sqlalchemy import text

    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate status (must be REVIEW to use chat)
    if draft_session.status != DraftSessionStatusEnum.REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chat only available when draft is in REVIEW status. "
                   f"Current status: {draft_session.status}"
        )

    # Validate draft_doc exists
    if not draft_session.draft_doc or not draft_session.draft_doc.get("content"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No draft content available to improve"
        )

    # Get current draft content (FULL content, not truncated)
    current_content = draft_session.draft_doc["content"]
    user_message = message.get("message", "")
    conversation_history = message.get("history", [])  # For future multi-turn support
    is_first_message = message.get("is_first_message", False)

    # Import draft tools
    from app.services.draft_tools import DraftTools

    # Check if this is a welcome message request (empty message, first interaction)
    # Only return welcome message if there's NO actual user message
    if not user_message and (is_first_message or not conversation_history):
        # Analyze document and generate welcome message
        analysis = DraftTools.analyze_document(current_content)
        welcome_msg = DraftTools.generate_welcome_message(
            analysis=analysis,
            document_type=draft_session.document_type or "Draft Document"
        )

        return {
            "draft_session_id": str(draft_session_id),
            "updated_content": current_content,  # No changes
            "ai_response": welcome_msg,
            "tools_used": ["analyze_document"],
            "tool_results": [{
                "tool": "analyze_document",
                "result": analysis
            }],
            "tokens_used": 0,  # No LLM tokens for welcome
            "iterations": draft_session.draft_doc.get("chat_iterations", 0),
            "is_welcome_message": True
        }

    # Process actual user message
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    # Get case to access documents
    case = db.query(Case).filter(Case.id == draft_session.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Define tools for GPT-5
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_case_documents",
                "description": "Search through case documents to find relevant information, facts, evidence, or citations. Use this when the user asks to add details, find information, or cite specific evidence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information in case documents"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_research_summary",
                "description": "Get the research summary that was created during draft generation. Contains key facts, legal issues, and relevant case law identified during research phase.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_document_structure",
                "description": "Analyze the document structure to understand sections, paragraphs, and organization. Use this before making structural edits to understand the document layout.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_section",
                "description": "Update an entire section of the document by its heading (e.g., 'FACTS', 'LEGAL ARGUMENT'). Use this for major rewrites of a section. SAFER than returning full document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section_heading": {
                            "type": "string",
                            "description": "The heading of the section to update (e.g., 'FACTS', 'PRAYER')"
                        },
                        "new_content": {
                            "type": "string",
                            "description": "The new content for this section (numbered paragraphs)"
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["replace", "append"],
                            "description": "Whether to replace the entire section or append to it (default: replace)",
                            "default": "replace"
                        }
                    },
                    "required": ["section_heading", "new_content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_paragraph",
                "description": "Update a specific paragraph by its number. Use this for targeted edits to individual paragraphs. SAFEST option for small changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paragraph_number": {
                            "type": "integer",
                            "description": "The paragraph number to update (e.g., 5)"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The new text for this paragraph (number will be added automatically)"
                        }
                    },
                    "required": ["paragraph_number", "new_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "insert_paragraph",
                "description": "Insert a new paragraph after a specified paragraph number. Subsequent paragraphs will be renumbered automatically. Use this to add new facts or arguments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "after_paragraph": {
                            "type": "integer",
                            "description": "Insert after this paragraph number (e.g., 5 will insert as new paragraph 6)"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The text for the new paragraph"
                        }
                    },
                    "required": ["after_paragraph", "new_text"]
                }
            }
        }
    ]

    # Initialize LLM provider with DB tracking
    llm_provider = LLMProvider(
        db=db,
        organisation_id=case.organisation_id,
        user_id=current_user.id,
        case_id=draft_session.case_id,
        resource_type="draft_session",
        resource_id=str(draft_session_id)
    )

    # Build system message with context
    system_message = """You are an expert South African litigation attorney helping users edit and improve legal documents.

**CRITICAL RULES:**
1. ALWAYS make the changes the user requests - don't just acknowledge or explain
2. Use STRUCTURED EDITING TOOLS instead of returning the full document
3. For small changes: use update_paragraph tool (SAFEST)
4. For section changes: use update_section tool
5. For adding content: use insert_paragraph tool
6. Only return full document as LAST RESORT if tools cannot be used

**Your Structured Editing Tools:**
- **analyze_document_structure**: Understand document layout before editing
- **update_paragraph**: Change a specific paragraph by number (SAFEST for small edits)
- **update_section**: Replace or append to entire sections (e.g., FACTS, PRAYER)
- **insert_paragraph**: Add new paragraphs with automatic renumbering
- **search_case_documents**: Find facts/evidence in case documents BEFORE editing
- **get_research_summary**: Get case context and legal issues

**How to Respond:**
1. If unsure about document structure → use analyze_document_structure FIRST
2. If user asks to add information → search_case_documents FIRST to find facts
3. If user requests fact-checking → search_case_documents to verify
4. For targeted changes → use update_paragraph or insert_paragraph
5. For major section rewrites → use update_section
6. After using tools → provide brief confirmation of changes made

**Editing Guidelines:**
- Maintain formal South African legal register
- Preserve document structure (headings in CAPITALS, numbered paragraphs)
- Preserve citation markers [1], [2], etc. - add new ones [N] when needed
- Always verify facts with search_case_documents before adding claims
- Use tools for safety - they prevent accidental document corruption
- Be concise in responses - the tools make the changes, you just confirm

**Example Workflow:**
User: "Update paragraph 5 to mention the contract was signed on 15 June 2023"
You:
1. search_case_documents(query="contract signed date June 2023")
2. update_paragraph(paragraph_number=5, new_text="The parties entered into a written agreement on 15 June 2023 [1], whereby...")
3. Respond: "✓ Updated paragraph 5 with contract date. Added citation [1] from signed agreement."

User: "Add a paragraph about the defendant's breach"
You:
1. search_case_documents(query="defendant breach contract obligations")
2. analyze_document_structure() [to know where to insert]
3. insert_paragraph(after_paragraph=10, new_text="The Defendant breached the agreement by...")
4. Respond: "✓ Inserted new paragraph 11 describing breach. Found supporting evidence in case documents."

DO NOT return the full document unless absolutely necessary. Use the tools."""

    # Build conversation messages
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"""**Current Draft (FOR REFERENCE ONLY - USE TOOLS TO EDIT):**
```
{current_content[:3000]}{"..." if len(current_content) > 3000 else ""}
```

**Document Information:**
- Document Type: {draft_session.document_type or 'Draft Document'}
- Title: {draft_session.title}
- Total Length: {len(current_content.split())} words
- Research Summary: {'Available' if draft_session.research_summary else 'Not available'}

**User Request:**
{user_message}

**IMPORTANT:**
- Use analyze_document_structure() to understand layout if needed
- Use search_case_documents() to verify facts BEFORE editing
- Use update_paragraph() / insert_paragraph() / update_section() to make changes
- DO NOT return the full document in your response - just confirm changes
- The tools will handle the actual editing safely"""}
    ]

    try:
        # Generate with tool calling support
        content, tool_calls, input_tokens, output_tokens = llm_provider.generate_with_tools(
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=1,  # GPT-5 requires temperature=1
            max_tokens=8000  # Increased from 4000 for comprehensive edits
        )

        tool_results = []
        tools_used = []

        # Track document changes made by tools
        document_modified = False
        modification_reports = []

        # Execute any tool calls
        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                tools_used.append(function_name)

                if function_name == "analyze_document_structure":
                    # Analyze document structure
                    analysis = DraftTools.analyze_document(current_content)

                    tool_results.append({
                        "tool": "analyze_document_structure",
                        "result": analysis
                    })

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(analysis)
                    })

                elif function_name == "update_paragraph":
                    # Update specific paragraph
                    para_num = function_args.get("paragraph_number")
                    new_text = function_args.get("new_text", "")

                    updated_content, report = DraftTools.update_paragraph(
                        content=current_content,
                        paragraph_number=para_num,
                        new_text=new_text
                    )

                    if report.get("success"):
                        current_content = updated_content
                        document_modified = True
                        modification_reports.append(report)

                    tool_results.append({
                        "tool": "update_paragraph",
                        "result": report
                    })

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(report)
                    })

                elif function_name == "update_section":
                    # Update entire section
                    section_heading = function_args.get("section_heading", "")
                    new_content_text = function_args.get("new_content", "")
                    operation = function_args.get("operation", "replace")

                    updated_content, report = DraftTools.update_section(
                        content=current_content,
                        section_heading=section_heading,
                        new_content=new_content_text,
                        operation=operation
                    )

                    if report.get("success"):
                        current_content = updated_content
                        document_modified = True
                        modification_reports.append(report)

                    tool_results.append({
                        "tool": "update_section",
                        "result": report
                    })

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(report)
                    })

                elif function_name == "insert_paragraph":
                    # Insert new paragraph
                    after_para = function_args.get("after_paragraph")
                    new_text = function_args.get("new_text", "")

                    updated_content, report = DraftTools.insert_paragraph(
                        content=current_content,
                        after_paragraph=after_para,
                        new_text=new_text
                    )

                    if report.get("success"):
                        current_content = updated_content
                        document_modified = True
                        modification_reports.append(report)

                    tool_results.append({
                        "tool": "insert_paragraph",
                        "result": report
                    })

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(report)
                    })

                elif function_name == "search_case_documents":
                    # Perform vector search on document chunks
                    query = function_args.get("query", "")
                    limit = function_args.get("limit", 5)

                    # Get all documents for this case
                    documents = db.query(Document).filter(
                        Document.case_id == draft_session.case_id,
                        Document.overall_status == "completed"
                    ).all()

                    # For now, do simple text search (TODO: implement vector search)
                    # Get chunks from these documents
                    doc_ids = [doc.id for doc in documents]
                    if doc_ids:
                        chunks = db.query(DocumentChunk).filter(
                            DocumentChunk.document_id.in_(doc_ids)
                        ).limit(limit * 3).all()  # Get more than needed for filtering

                        # Simple text matching (TODO: replace with vector similarity)
                        query_lower = query.lower()
                        matching_chunks = [
                            chunk for chunk in chunks
                            if query_lower in chunk.text_content.lower()
                        ][:limit]

                        results = []
                        for chunk in matching_chunks:
                            doc = db.query(Document).filter(Document.id == chunk.document_id).first()
                            results.append({
                                "document": doc.filename if doc else "Unknown",
                                "page": chunk.page_number,
                                "content": chunk.text_content[:500]  # Limit excerpt length
                            })

                        tool_results.append({
                            "tool": "search_case_documents",
                            "result": results
                        })

                        # Add tool result to conversation
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(results)
                        })

                elif function_name == "get_research_summary":
                    # Return research summary from draft session
                    summary = draft_session.research_summary or {"message": "No research summary available"}

                    tool_results.append({
                        "tool": "get_research_summary",
                        "result": summary
                    })

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(summary)
                    })

            # Generate final response with tool results
            final_content, _, final_input_tokens, final_output_tokens = llm_provider.generate_with_tools(
                messages=messages,
                tools=None,  # No more tool calls needed
                temperature=1,
                max_tokens=8000
            )

            input_tokens += final_input_tokens
            output_tokens += final_output_tokens
            content = final_content

        # Determine final content
        # If tools modified the document, use current_content
        # Otherwise, check if AI returned full document in content
        if document_modified:
            updated_content = current_content
        else:
            # Legacy behavior: AI might return full document (discouraged now)
            updated_content = content if content and len(content) > 500 else current_content

        # Update draft_doc with new content
        draft_session.draft_doc["content"] = updated_content
        draft_session.draft_doc["chat_iterations"] = draft_session.draft_doc.get("chat_iterations", 0) + 1
        draft_session.draft_doc["last_chat_at"] = __import__('datetime').datetime.utcnow().isoformat()

        # Track modification reports
        if modification_reports:
            if "modification_history" not in draft_session.draft_doc:
                draft_session.draft_doc["modification_history"] = []
            draft_session.draft_doc["modification_history"].extend(modification_reports)

        db.flush()
        db.commit()

        return {
            "draft_session_id": str(draft_session_id),
            "updated_content": updated_content,
            "ai_response": content,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "tokens_used": input_tokens + output_tokens,
            "iterations": draft_session.draft_doc.get("chat_iterations", 1),
            "document_modified": document_modified,
            "modifications": modification_reports
        }

    except Exception as e:
        import traceback
        logger.error(f"Chat with draft failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )


@router.get("/{draft_session_id}/citations", response_model=CitationsListResponse)
def get_draft_citations(
    draft_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get citations for a draft session (Audit mode).

    Returns all citations with source excerpts for verification.
    Used in Audit mode to show side-by-side source documents.

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of citations with source document excerpts

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not yet generated (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate draft has been generated
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Citations not available for draft in {draft_session.status} status. "
                   f"Draft must be generated first."
        )

    # Query citations from Citation model
    citation_repo = CitationRepository(db)
    citations_with_doc_info = citation_repo.get_with_document_info(draft_session_id)

    # Convert to CitationResponse objects
    citations_data = []
    for citation_dict in citations_with_doc_info:
        citations_data.append(CitationResponse(
            marker=citation_dict["marker"],
            content=citation_dict["citation_text"],
            document_name=citation_dict["document_filename"] or "Unknown",
            document_id=citation_dict["document_id"] or "",
            page=citation_dict["page_number"],
            similarity=citation_dict["similarity_score"]
        ))

    return CitationsListResponse(
        draft_session_id=draft_session_id,
        citations=citations_data,
        total_citations=len(citations_data)
    )


@router.get("/{draft_session_id}/export/pdf")
def export_draft_to_pdf(
    draft_session_id: str,
    citation_format: Literal["endnotes", "inline", "none"] = Query("endnotes", description="Citation format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export draft session to PDF.

    Returns court-ready PDF with proper formatting for South African legal documents.
    Supports different citation formats:
    - endnotes: Citations as footnotes at end of document
    - inline: Citations inline within text
    - none: Remove all citation markers

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        citation_format: Citation formatting mode (default: endnotes)
        db: Database session
        current_user: Current authenticated user

    Returns:
        PDF file download (application/pdf)

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not ready for export (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate draft has been generated
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Draft not ready for export. Current status: {draft_session.status}. "
                   f"Draft must be in REVIEW or READY status."
        )

    # Validate draft_doc exists
    if not draft_session.draft_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft content not available. Please regenerate the draft."
        )

    # Generate PDF
    export_service = DraftExportService()

    try:
        pdf_buffer = export_service.export_to_pdf(
            draft_doc=draft_session.draft_doc,
            document_type=draft_session.document_type,
            title=draft_session.title,
            citation_format=citation_format
        )

        # Create safe filename
        safe_title = draft_session.title.replace(" ", "_").replace("/", "_")[:50]
        filename = f"{safe_title}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/{draft_session_id}/export/docx")
def export_draft_to_docx(
    draft_session_id: str,
    citation_format: Literal["endnotes", "inline", "none"] = Query("endnotes", description="Citation format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export draft session to DOCX (Word format).

    Returns court-ready DOCX document with proper formatting for South African legal documents.
    Supports different citation formats:
    - endnotes: Citations as footnotes at end of document
    - inline: Citations inline within text
    - none: Remove all citation markers

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        citation_format: Citation formatting mode (default: endnotes)
        db: Database session
        current_user: Current authenticated user

    Returns:
        DOCX file download (application/vnd.openxmlformats-officedocument.wordprocessingml.document)

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not ready for export (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate draft has been generated
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Draft not ready for export. Current status: {draft_session.status}. "
                   f"Draft must be in REVIEW or READY status."
        )

    # Validate draft_doc exists
    if not draft_session.draft_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft content not available. Please regenerate the draft."
        )

    # Generate DOCX
    export_service = DraftExportService()

    try:
        docx_buffer = export_service.export_to_docx(
            draft_doc=draft_session.draft_doc,
            document_type=draft_session.document_type,
            title=draft_session.title,
            citation_format=citation_format
        )

        # Create safe filename
        safe_title = draft_session.title.replace(" ", "_").replace("/", "_")[:50]
        filename = f"{safe_title}.docx"

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate DOCX: {str(e)}"
        )


@router.get("/{draft_session_id}/export/markdown")
def export_draft_to_markdown(
    draft_session_id: str,
    citation_format: Literal["endnotes", "inline", "none"] = Query("endnotes", description="Citation format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export draft session to Markdown (.md) format.

    Returns Markdown-formatted document with proper structure.
    Supports different citation formats:
    - endnotes: Citations as references at end of document
    - inline: Citations inline within text
    - none: Remove all citation markers

    Requires authentication.

    Args:
        draft_session_id: Draft session ID (UUID)
        citation_format: Citation formatting mode (default: endnotes)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Markdown file download (text/markdown)

    Raises:
        HTTPException: If draft session not found (404)
        HTTPException: If draft not ready for export (400)
    """
    draft_repo = DraftSessionRepository(db)
    draft_session = draft_repo.get_by_id(draft_session_id)

    if not draft_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft session not found"
        )

    # Validate draft has been generated
    if draft_session.status not in [
        DraftSessionStatusEnum.REVIEW,
        DraftSessionStatusEnum.READY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Draft not ready for export. Current status: {draft_session.status}. "
                   f"Draft must be in REVIEW or READY status."
        )

    # Validate draft_doc exists
    if not draft_session.draft_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft content not available. Please regenerate the draft."
        )

    # Generate Markdown
    export_service = DraftExportService()

    try:
        md_buffer = export_service.export_to_markdown(
            draft_doc=draft_session.draft_doc,
            document_type=draft_session.document_type,
            title=draft_session.title,
            citation_format=citation_format
        )

        # Create safe filename
        safe_title = draft_session.title.replace(" ", "_").replace("/", "_")[:50]
        filename = f"{safe_title}.md"

        return StreamingResponse(
            md_buffer,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Markdown: {str(e)}"
        )
