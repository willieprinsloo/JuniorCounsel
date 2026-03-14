"""
Case endpoints for CRUD operations with pagination.
"""
from typing import Optional, List, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, CaseStatusEnum, Document, Rulebook
from app.persistence.repositories import CaseRepository, DraftSessionRepository
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse
from app.schemas.document_assistant import (
    DocumentChatRequest,
    DocumentChatResponse,
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    ToolResult,
    SuggestedAction
)
from app.services.document_analysis import DocumentAnalysisService
from app.core.ai_providers import get_llm_provider

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new case.

    Requires authentication.

    Args:
        case_data: Case creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created case object
    """
    try:
        case_repo = CaseRepository(db)
        case = case_repo.create(
            organisation_id=case_data.organisation_id,
            title=case_data.title,
            owner_id=case_data.owner_id or current_user.id,
            description=case_data.description,
            case_type=case_data.case_type,
            jurisdiction=case_data.jurisdiction
        )
        db.commit()
        db.refresh(case)

        # Manually construct response to ensure UUID is converted
        return CaseResponse(
            id=str(case.id),
            organisation_id=case.organisation_id,
            owner_id=case.owner_id,
            title=case.title,
            description=case.description,
            case_type=case.case_type,
            jurisdiction=case.jurisdiction,
            status=case.status,
            case_metadata=case.case_metadata,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating case: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create case: {str(e)}"
        )


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a case by ID.

    Requires authentication.

    Args:
        case_id: Case ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Case object

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return CaseResponse(
        id=str(case.id),
        organisation_id=case.organisation_id,
        owner_id=case.owner_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        jurisdiction=case.jurisdiction,
        status=case.status,
        case_metadata=case.case_metadata,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("/", response_model=CaseListResponse)
def list_cases(
    organisation_id: int = Query(..., description="Organisation ID to filter cases"),
    status: Optional[CaseStatusEnum] = Query(None, description="Filter by case status"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    q: Optional[str] = Query(None, description="Search query (title, description)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List cases with pagination and filtering.

    Requires authentication.

    Args:
        organisation_id: Organisation ID (required)
        status: Filter by case status
        case_type: Filter by case type
        q: Search query
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of cases
    """
    case_repo = CaseRepository(db)
    cases, total = case_repo.list(
        organisation_id=organisation_id,
        status=status,
        case_type=case_type,
        q=q,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    # Convert cases to response objects with proper UUID handling
    case_responses = [
        CaseResponse(
            id=str(case.id),
            organisation_id=case.organisation_id,
            owner_id=case.owner_id,
            title=case.title,
            description=case.description,
            case_type=case.case_type,
            jurisdiction=case.jurisdiction,
            status=case.status,
            case_metadata=case.case_metadata,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        for case in cases
    ]

    return {
        "data": case_responses,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    case_data: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a case.

    Requires authentication. Only updates provided fields.

    Args:
        case_id: Case ID (UUID)
        case_data: Case update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated case object

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Update only provided fields
    if case_data.title is not None:
        case.title = case_data.title
    if case_data.description is not None:
        case.description = case_data.description
    if case_data.case_type is not None:
        case.case_type = case_data.case_type
    if case_data.jurisdiction is not None:
        case.jurisdiction = case_data.jurisdiction
    if case_data.status is not None:
        case.status = case_data.status

    db.commit()
    db.refresh(case)

    return CaseResponse(
        id=str(case.id),
        organisation_id=case.organisation_id,
        owner_id=case.owner_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        jurisdiction=case.jurisdiction,
        status=case.status,
        case_metadata=case.case_metadata,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a case.

    Requires authentication.

    Args:
        case_id: Case ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If case not found (404)
    """
    case_repo = CaseRepository(db)
    deleted = case_repo.delete(case_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )


# ===== Document Assistant Endpoints =====


@router.post("/{case_id}/documents/analyze", response_model=DocumentAnalysisResponse)
def analyze_case_documents(
    case_id: str,
    request: DocumentAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze all completed documents in a case to extract key facts, parties, and dates.

    This endpoint is used by the Document Assistant to provide intelligent summaries.

    Args:
        case_id: Case ID (UUID)
        request: Analysis request with type
        db: Database session
        current_user: Current authenticated user

    Returns:
        Structured analysis with parties, dates, facts, and warnings

    Raises:
        HTTPException: If case not found (404)
    """
    # Verify case exists
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Perform analysis
    try:
        analysis_result = DocumentAnalysisService.analyze_case_documents(
            case_id=case_id,
            db=db,
            analysis_type=request.analysis_type
        )
        return analysis_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/{case_id}/documents/chat", response_model=DocumentChatResponse)
def chat_with_documents(
    case_id: str,
    request: DocumentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the Document Assistant about case documents.

    The assistant can:
    - Analyze documents to extract key information
    - Answer questions about case materials
    - Initiate draft sessions
    - List available document templates

    Args:
        case_id: Case ID (UUID)
        request: Chat request with message and history
        db: Database session
        current_user: Current authenticated user

    Returns:
        AI response with tool results and suggested actions

    Raises:
        HTTPException: If case not found (404)
    """
    # Verify case exists
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Get document count for context
    documents = db.query(Document).filter(Document.case_id == case_id).all()
    completed_docs = [d for d in documents if d.overall_status == 'completed']

    # Define AI tools for the Document Assistant
    tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_case_documents",
                "description": "Analyze all completed documents in the case to extract key parties, dates, and facts. Use this when user asks to 'scan documents', 'analyze documents', or wants a summary of the case materials.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["full", "summary", "key_facts"],
                            "description": "Type of analysis: full (all details), summary (brief overview), key_facts (just critical facts)"
                        }
                    },
                    "required": ["analysis_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "initiate_draft_session",
                "description": "Start creating a new draft document (affidavit, pleading, heads of argument). Use this when user wants to 'start a draft', 'create an affidavit', or 'draft a document'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_type": {
                            "type": "string",
                            "description": "Type of document to draft (e.g., 'Affidavit', 'Notice of Motion', 'Heads of Argument')"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the draft session (e.g., 'Founding Affidavit - Smith v Jones')"
                        },
                        "rulebook_id": {
                            "type": "integer",
                            "description": "ID of the rulebook to use"
                        }
                    },
                    "required": ["document_type", "title", "rulebook_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_available_rulebooks",
                "description": "Get list of available document templates/rulebooks. Use this when user asks 'what can I draft?' or 'what documents are available?'",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    # Build system prompt
    system_prompt = f"""You are the Document Assistant for Junior Counsel, a legal document processing system for South African litigation practice.

Your role is to help practitioners:
1. **Understand their case documents** - Analyze uploaded documents to find key facts, parties, dates, and potential issues
2. **Start drafting efficiently** - Guide users through creating affidavits, pleadings, or heads of argument
3. **Navigate the system** - Provide friendly help and explanations

**Context**: You are currently assisting with Case ID {case_id}, which has {len(documents)} document(s) ({len(completed_docs)} completed).

**Available Tools**:
- `analyze_case_documents`: Scan all documents to extract structured information
- `list_available_rulebooks`: Show available document templates (CALL THIS FIRST before initiating a draft!)
- `initiate_draft_session`: Start creating a new draft document (requires rulebook_id from list_available_rulebooks)

**Important Workflow for Creating Drafts**:
1. User asks to create a draft (e.g., "create a plea", "draft an affidavit")
2. FIRST call `list_available_rulebooks` to see what templates are available
3. Choose the appropriate rulebook based on document_type and jurisdiction
4. THEN call `initiate_draft_session` with the chosen rulebook_id
5. Tell user "I've created a draft session. You'll now answer a few questions before we generate the document."

**Guidelines**:
1. **Be proactive**: Offer to analyze documents when user first interacts
2. **Be clear**: Use simple language, avoid legal jargon in your explanations
3. **Be cautious**: Always remind users to verify critical facts themselves
4. **Be helpful**: Guide users step-by-step through creating drafts
5. **Cite sources**: When mentioning facts, reference the source document and page
6. **Always get rulebooks first**: Never try to initiate a draft without first calling list_available_rulebooks

**Warnings to include**:
- After document analysis: "⚠️ These are AI-extracted facts. Always verify critical information yourself."
- Before initiating draft: "This will create a new draft session. You'll answer intake questions before generation begins."

**Tone**: Friendly, professional, and supportive. Think of yourself as a helpful junior associate."""

    # Build conversation messages
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in request.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current user message
    if request.message:
        messages.append({"role": "user", "content": request.message})

    # Call LLM with tools
    llm_provider = get_llm_provider()
    tools_used = []
    tool_results = []
    draft_session_id = None

    try:
        content, tool_calls, input_tokens, output_tokens = llm_provider.generate_with_tools(
            messages=messages,
            tools=tools,
            temperature=0.7
        )

        response = {
            "content": content,
            "tool_calls": tool_calls,
            "message": {"role": "assistant", "content": content, "tool_calls": tool_calls},
            "usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}
        }

        # Check if tools were called
        if response.get("tool_calls"):
            for tool_call in response["tool_calls"]:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                tools_used.append(function_name)

                # Execute tool
                if function_name == "analyze_case_documents":
                    analysis_result = DocumentAnalysisService.analyze_case_documents(
                        case_id=case_id,
                        db=db,
                        analysis_type=function_args.get("analysis_type", "full")
                    )
                    tool_results.append(ToolResult(
                        tool=function_name,
                        result=analysis_result
                    ))

                elif function_name == "list_available_rulebooks":
                    rulebooks = db.query(Rulebook).filter(
                        Rulebook.status == 'published'
                    ).all()
                    rulebook_list = [
                        {
                            "id": rb.id,
                            "label": rb.label or f"{rb.document_type} - {rb.jurisdiction}",
                            "document_type": rb.document_type,
                            "jurisdiction": rb.jurisdiction,
                            "version": rb.version
                        }
                        for rb in rulebooks
                    ]
                    tool_results.append(ToolResult(
                        tool=function_name,
                        result={"rulebooks": rulebook_list}
                    ))

                elif function_name == "initiate_draft_session":
                    # Create draft session
                    from app.persistence.models import DraftSessionStatusEnum

                    draft_repo = DraftSessionRepository(db)
                    draft_session = draft_repo.create(
                        case_id=case_id,
                        user_id=current_user.id,
                        rulebook_id=function_args["rulebook_id"],
                        title=function_args["title"],
                        document_type=function_args["document_type"]
                    )

                    # Set to awaiting_intake status so user can answer questions
                    draft_session.status = DraftSessionStatusEnum.AWAITING_INTAKE
                    db.flush()
                    db.commit()
                    db.refresh(draft_session)
                    draft_session_id = str(draft_session.id)

                    tool_results.append(ToolResult(
                        tool=function_name,
                        result={
                            "draft_session_id": draft_session_id,
                            "title": draft_session.title,
                            "status": draft_session.status.value,
                            "message": "Draft session created! User will be directed to answer intake questions before generation begins."
                        }
                    ))

            # Get final response after tool execution
            # Add tool results back to conversation
            tool_messages = []
            for i, tool_call in enumerate(response["tool_calls"]):
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_results[i].result)
                })

            # Call LLM again with tool results
            final_content, _, _, _ = llm_provider.generate_with_tools(
                messages=messages + [response["message"]] + tool_messages,
                tools=tools,
                temperature=0.7
            )
            ai_response = final_content
        else:
            # No tool calls, just return the response
            ai_response = response["content"]

        # Generate suggested actions
        suggested_actions = []
        if "analyze" in ai_response.lower() and len(completed_docs) > 0:
            suggested_actions.append(SuggestedAction(
                action="analyze_documents",
                label="Analyze Documents"
            ))

        if draft_session_id:
            suggested_actions.append(SuggestedAction(
                action="view_draft",
                label="View Draft Session",
                metadata={"draft_session_id": draft_session_id}
            ))

        return DocumentChatResponse(
            ai_response=ai_response,
            tools_used=tools_used,
            tool_results=tool_results,
            suggested_actions=suggested_actions,
            draft_session_id=draft_session_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )
