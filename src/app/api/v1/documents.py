"""
Document endpoints for CRUD operations with pagination.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DocumentStatusEnum
from app.persistence.repositories import DocumentRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentStatusUpdate,
    DocumentResponse,
    DocumentListResponse,
)

router = APIRouter()


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    doc_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new document.

    Requires authentication. Typically called after file upload.

    Args:
        doc_data: Document creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created document object (status: queued)
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.create(
        case_id=doc_data.case_id,
        uploaded_by_id=current_user.id,
        filename=doc_data.filename,
        upload_session_id=doc_data.upload_session_id,
        needs_ocr=doc_data.needs_ocr
    )
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a document by ID.

    Requires authentication.

    Args:
        document_id: Document ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Document object

    Raises:
        HTTPException: If document not found (404)
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    case_id: str = Query(..., description="Case ID to filter documents"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[DocumentStatusEnum] = Query(None, description="Filter by status"),
    q: Optional[str] = Query(None, description="Search query (filename)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List documents with pagination and filtering.

    Requires authentication.

    Args:
        case_id: Case ID (required)
        document_type: Filter by document type
        status: Filter by overall_status
        q: Search query
        page: Page number
        per_page: Items per page
        sort: Sort field
        order: Sort order (asc/desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of documents
    """
    doc_repo = DocumentRepository(db)
    documents, total = doc_repo.list(
        case_id=case_id,
        document_type=document_type,
        status=status,
        q=q,
        page=page,
        per_page=per_page,
        sort=sort,
        order=order
    )

    # Calculate next page
    next_page = page + 1 if (page * per_page) < total else None

    return {
        "data": documents,
        "page": page,
        "per_page": per_page,
        "total": total,
        "next_page": next_page
    }


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    doc_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update document metadata.

    Requires authentication. Only updates provided fields.

    Args:
        document_id: Document ID (UUID)
        doc_data: Document update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated document object

    Raises:
        HTTPException: If document not found (404)
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Update only provided fields
    if doc_data.document_type is not None:
        document.document_type = doc_data.document_type
    if doc_data.semantic_role is not None:
        document.semantic_role = doc_data.semantic_role
    if doc_data.tags is not None:
        document.tags = doc_data.tags

    db.flush()
    return document


@router.patch("/{document_id}/status", response_model=DocumentResponse)
def update_document_status(
    document_id: str,
    status_data: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update document processing status.

    Requires authentication. Used by workers to update processing progress.

    Args:
        document_id: Document ID (UUID)
        status_data: Status update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated document object

    Raises:
        HTTPException: If document not found (404)
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.update_status(
        document_id=document_id,
        overall_status=status_data.overall_status,
        stage=status_data.stage,
        stage_progress=status_data.stage_progress,
        error_message=status_data.error_message
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document.

    Requires authentication.

    Args:
        document_id: Document ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If document not found (404)
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    db.delete(document)
    db.flush()
