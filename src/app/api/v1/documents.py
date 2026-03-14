"""
Document endpoints for CRUD operations with pagination.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.queue import enqueue_document_processing
from app.core.storage import storage, detect_needs_ocr
from app.dependencies import get_current_user
from app.middleware.database import get_db
from app.persistence.models import User, DocumentStatusEnum
from app.persistence.repositories import DocumentRepository, UploadSessionRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentStatusUpdate,
    DocumentResponse,
    DocumentListResponse,
)

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    file: UploadFile = File(..., description="Document file to upload (PDF, DOCX, images)"),
    case_id: str = Form(..., description="Case ID this document belongs to"),
    upload_session_id: Optional[str] = Form(None, description="Optional upload session for batch tracking"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document file and enqueue for processing.

    This endpoint handles multipart/form-data file uploads, saves the file to storage,
    creates a Document record, and enqueues a background processing job.

    Processing stages (handled by worker):
    1. OCR (if needed)
    2. Text extraction
    3. Chunking
    4. Embedding generation
    5. Vector indexing
    6. Classification

    Args:
        file: Uploaded file
        case_id: Case ID (UUID)
        upload_session_id: Optional UploadSession ID for batch tracking
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created document with status="queued"

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/documents/upload \
          -H "Authorization: Bearer {token}" \
          -F "file=@contract.pdf" \
          -F "case_id=550e8400-e29b-41d4-a716-446655440000"
        ```
    """
    # Validate file size
    max_size_bytes = (settings.MAX_UPLOAD_SIZE_MB or 50) * 1024 * 1024
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Validate file extension
    allowed_extensions = (settings.ALLOWED_EXTENSIONS or "pdf,docx,doc,jpg,png").split(",")
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        )

    # Detect if OCR is needed
    needs_ocr = detect_needs_ocr(file)

    # Save file to storage
    try:
        file_path, storage_url = storage.save_file(file, case_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Create Document record
    doc_repo = DocumentRepository(db)
    try:
        document = doc_repo.create(
            case_id=case_id,
            uploaded_by_id=current_user.id,
            filename=file.filename,
            upload_session_id=upload_session_id,
            needs_ocr=needs_ocr
        )

        # Store file path and size in document model
        document.file_path = file_path
        document.file_size = file_size
        db.flush()
        db.commit()
    except Exception as e:
        db.rollback()
        # Delete the uploaded file since we couldn't create the database record
        try:
            storage.delete_file(file_path)
        except:
            pass

        # Check for specific constraint violations
        error_msg = str(e)
        if "uq_case_document" in error_msg or "unique constraint" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A document with the filename '{file.filename}' already exists in this case. Please rename the file or delete the existing document first."
            )
        elif "foreign key" in error_msg.lower():
            if "case_id" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Case with ID '{case_id}' not found. Please check the case ID and try again."
                )
            elif "user" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User account not found. Please log in again."
                )
            elif "upload_session" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upload session '{upload_session_id}' not found. Please start a new upload session."
                )

        # Generic database error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document record: {error_msg}"
        )

    # Enqueue processing job (non-blocking)
    try:
        job_id = enqueue_document_processing(document.id)
        db.flush()
        db.commit()
    except Exception as e:
        # Log error but don't fail the upload
        # User can manually retry processing later
        document.error_message = f"Failed to enqueue job: {str(e)}"
        db.flush()
        db.commit()

    # Update upload session counters if provided
    if upload_session_id:
        session_repo = UploadSessionRepository(db)
        session_repo.update_counts(upload_session_id, completed_increment=0, failed_increment=0)
        # Note: counts updated by worker on completion/failure

    return document


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
    Delete a document and all associated data.

    This endpoint deletes:
    - The document record from database
    - All associated vector embeddings (DocumentChunks) via CASCADE
    - The physical file from storage

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

    # Delete physical file if it exists
    if document.file_path:
        try:
            storage.delete_file(document.file_path)
        except Exception as e:
            # Log error but continue with database deletion
            # The file might already be gone or storage might be unavailable
            pass

    # Delete from database (chunks will be cascade deleted via foreign key)
    db.delete(document)
    db.flush()
    db.commit()


@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry_document_processing(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry processing for a failed or stuck document.

    Resets the document status to QUEUED and enqueues a new processing job.
    Useful for documents that failed due to temporary issues (network, dependencies, etc.).

    Args:
        document_id: Document ID (UUID)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Document object with reset status

    Raises:
        HTTPException: If document not found (404)

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/documents/{id}/retry \
          -H "Authorization: Bearer {token}"
        ```
    """
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Reset status
    document.overall_status = DocumentStatusEnum.QUEUED
    document.stage = None
    document.stage_progress = 0
    document.error_message = None
    db.flush()
    db.commit()

    # Enqueue processing job
    try:
        job_id = enqueue_document_processing(document.id)
        db.commit()
    except Exception as e:
        document.error_message = f"Failed to enqueue job: {str(e)}"
        db.flush()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue processing job: {str(e)}"
        )

    return document
