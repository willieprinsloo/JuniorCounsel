"""
Chat session endpoints for persistent Q&A conversations.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User
from app.persistence.chat_session_repository import ChatSessionRepository, ChatMessageRepository
from app.persistence.repositories import CaseRepository
from app.schemas.chat_session import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatMessageResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_create: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new chat session for Q&A conversations.

    Args:
        session_create: Chat session creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created chat session
    """
    # Verify case exists and user has access
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(UUID(session_create.case_id))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Create chat session
    chat_repo = ChatSessionRepository(db)
    chat_session = chat_repo.create(
        case_id=UUID(session_create.case_id),
        user_id=current_user.id,
        title=session_create.title
    )

    logger.info(f"Created chat session {chat_session.id} for case {case.id} by user {current_user.id}")

    # Build response with message count
    message_count = chat_repo.get_message_count(chat_session.id)

    return ChatSessionResponse(
        id=str(chat_session.id),
        case_id=str(chat_session.case_id),
        user_id=chat_session.user_id,
        title=chat_session.title,
        message_count=message_count,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at
    )


@router.get("/", response_model=ChatSessionListResponse)
def list_chat_sessions(
    case_id: str,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List chat sessions for a case.

    Args:
        case_id: Case ID to filter by
        page: Page number (1-indexed)
        per_page: Results per page (max 100)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of chat sessions
    """
    per_page = min(per_page, 100)

    # Verify case exists and user has access
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(UUID(case_id))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Get chat sessions
    chat_repo = ChatSessionRepository(db)
    sessions, total = chat_repo.list_by_case(UUID(case_id), page, per_page)

    # Build responses with message counts
    session_responses = []
    for session in sessions:
        message_count = chat_repo.get_message_count(session.id)
        session_responses.append(
            ChatSessionResponse(
                id=str(session.id),
                case_id=str(session.case_id),
                user_id=session.user_id,
                title=session.title,
                message_count=message_count,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
        )

    next_page = page + 1 if page * per_page < total else None

    return ChatSessionListResponse(
        data=session_responses,
        page=page,
        per_page=per_page,
        total=total,
        next_page=next_page
    )


@router.get("/{chat_session_id}", response_model=ChatSessionDetailResponse)
def get_chat_session(
    chat_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a chat session with full message history.

    Args:
        chat_session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Chat session with all messages
    """
    chat_repo = ChatSessionRepository(db)
    chat_session = chat_repo.get_by_id(UUID(chat_session_id))

    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )

    # Verify user has access (must be the owner)
    if chat_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get all messages
    message_repo = ChatMessageRepository(db)
    messages = message_repo.list_by_session(chat_session.id)

    # Build message responses
    message_responses = [
        ChatMessageResponse(
            id=str(msg.id),
            chat_session_id=str(msg.chat_session_id),
            question=msg.question,
            answer=msg.answer,
            confidence=msg.confidence,
            sources=msg.sources,
            created_at=msg.created_at
        )
        for msg in messages
    ]

    return ChatSessionDetailResponse(
        id=str(chat_session.id),
        case_id=str(chat_session.case_id),
        user_id=chat_session.user_id,
        title=chat_session.title,
        messages=message_responses,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at
    )


@router.delete("/{chat_session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    chat_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a chat session and all its messages.

    Args:
        chat_session_id: Chat session ID
        db: Database session
        current_user: Current authenticated user
    """
    chat_repo = ChatSessionRepository(db)
    chat_session = chat_repo.get_by_id(UUID(chat_session_id))

    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )

    # Verify user has access (must be the owner)
    if chat_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete chat session (cascades to messages)
    chat_repo.delete(chat_session.id)

    logger.info(f"Deleted chat session {chat_session_id} by user {current_user.id}")
