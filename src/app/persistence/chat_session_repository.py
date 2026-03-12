"""
Repository for ChatSession and ChatMessage data access.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.persistence.models import ChatSession, ChatMessage


class ChatSessionRepository:
    """Repository for ChatSession operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, case_id: UUID, user_id: int, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        chat_session = ChatSession(
            case_id=case_id,
            user_id=user_id,
            title=title
        )
        self.session.add(chat_session)
        self.session.flush()
        return chat_session

    def get_by_id(self, chat_session_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        return self.session.get(ChatSession, chat_session_id)

    def list_by_case(
        self,
        case_id: UUID,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[ChatSession], int]:
        """List chat sessions for a case with pagination."""
        offset = (page - 1) * per_page

        # Get total count
        total_stmt = select(func.count()).select_from(ChatSession).where(
            ChatSession.case_id == case_id
        )
        total = self.session.execute(total_stmt).scalar() or 0

        # Get paginated results
        stmt = (
            select(ChatSession)
            .where(ChatSession.case_id == case_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        sessions = list(self.session.scalars(stmt).all())

        return sessions, total

    def list_by_user(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[list[ChatSession], int]:
        """List chat sessions for a user with pagination."""
        offset = (page - 1) * per_page

        # Get total count
        total_stmt = select(func.count()).select_from(ChatSession).where(
            ChatSession.user_id == user_id
        )
        total = self.session.execute(total_stmt).scalar() or 0

        # Get paginated results
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        sessions = list(self.session.scalars(stmt).all())

        return sessions, total

    def update_title(self, chat_session_id: UUID, title: str) -> Optional[ChatSession]:
        """Update chat session title."""
        chat_session = self.get_by_id(chat_session_id)
        if chat_session:
            chat_session.title = title
            self.session.flush()
        return chat_session

    def delete(self, chat_session_id: UUID) -> bool:
        """Delete a chat session (cascades to messages)."""
        chat_session = self.get_by_id(chat_session_id)
        if chat_session:
            self.session.delete(chat_session)
            self.session.flush()
            return True
        return False

    def get_message_count(self, chat_session_id: UUID) -> int:
        """Get count of messages in a chat session."""
        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.chat_session_id == chat_session_id
        )
        return self.session.execute(stmt).scalar() or 0


class ChatMessageRepository:
    """Repository for ChatMessage operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        chat_session_id: UUID,
        question: str,
        answer: str,
        confidence: float,
        sources: Optional[list[dict]] = None
    ) -> ChatMessage:
        """Create a new chat message (Q&A exchange)."""
        message = ChatMessage(
            chat_session_id=chat_session_id,
            question=question,
            answer=answer,
            confidence=confidence,
            sources=sources or []
        )
        self.session.add(message)
        self.session.flush()
        return message

    def get_by_id(self, message_id: UUID) -> Optional[ChatMessage]:
        """Get a chat message by ID."""
        return self.session.get(ChatMessage, message_id)

    def list_by_session(
        self,
        chat_session_id: UUID,
        limit: Optional[int] = None
    ) -> list[ChatMessage]:
        """List all messages in a chat session, ordered chronologically."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == chat_session_id)
            .order_by(ChatMessage.created_at.asc())
        )

        if limit:
            stmt = stmt.limit(limit)

        return list(self.session.scalars(stmt).all())

    def delete(self, message_id: UUID) -> bool:
        """Delete a chat message."""
        message = self.get_by_id(message_id)
        if message:
            self.session.delete(message)
            self.session.flush()
            return True
        return False
