"""
Document processing worker.

Handles the complete document processing pipeline:
1. OCR (if needed)
2. Text extraction
3. Chunking
4. Embedding generation
5. Vector indexing
6. Document classification
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.ai_providers import get_embedding_provider, get_llm_provider
from app.persistence.models import DocumentStatusEnum, DocumentChunk, TokenUsageTypeEnum
from app.persistence.repositories import DocumentRepository, TokenUsageRepository
from app.workers.ocr import perform_ocr
from app.workers.text_extraction import extract_text
from app.workers.chunking import chunk_text, extract_page_number

logger = logging.getLogger(__name__)


def process_document_job(document_id: str):
    """
    Process a document through the complete pipeline.

    This is the main RQ job handler. It coordinates all processing stages
    and updates status at each step.

    Args:
        document_id: Document ID (UUID)

    Raises:
        Exception: If processing fails (will be retried by RQ)
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        doc_repo = DocumentRepository(db)

        # Get document
        document = doc_repo.get_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Starting processing for document {document_id}: {document.filename}")

        # Get file path from metadata
        if not document.metadata or 'storage_url' not in document.metadata:
            raise ValueError(f"Document {document_id} has no file path in metadata")

        file_path = document.metadata['storage_url']

        # Update status to processing
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="initializing",
            stage_progress=0
        )
        db.commit()

        # Stage 1: Text Extraction (with OCR if needed)
        logger.info(f"[{document_id}] Stage 1: Text extraction (OCR={document.needs_ocr})")
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="text_extraction" if not document.needs_ocr else "ocr",
            stage_progress=10
        )
        db.commit()

        try:
            # extract_text handles both OCR and regular extraction
            extracted_text = extract_text(file_path, needs_ocr=document.needs_ocr)

            if not extracted_text or len(extracted_text.strip()) < 50:
                raise ValueError("Insufficient text extracted from document")

            logger.info(f"[{document_id}] Extracted {len(extracted_text)} characters")

            # Store OCR confidence if available
            if document.needs_ocr and document.metadata:
                # OCR returns {"text": ..., "confidence": ..., "page_count": ...}
                # But extract_text only returns text, so we'd need to call perform_ocr separately
                # For now, just note that OCR was used
                document.metadata['extraction_method'] = 'ocr'
            else:
                document.metadata['extraction_method'] = 'text'

            db.flush()

        except Exception as e:
            logger.error(f"[{document_id}] Text extraction failed: {e}")
            raise RuntimeError(f"Text extraction failed: {str(e)}")

        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="text_extraction",
            stage_progress=30
        )
        db.commit()

        # Stage 2: Chunking
        logger.info(f"[{document_id}] Stage 2: Chunking")
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="chunking",
            stage_progress=40
        )
        db.commit()

        try:
            # Chunk text into semantic segments
            chunks = chunk_text(
                text=extracted_text,
                chunk_size=512,  # ~512 tokens per chunk
                chunk_overlap=50,  # 50 tokens overlap for context
                min_chunk_size=100  # Skip very small chunks
            )

            if not chunks:
                raise ValueError("No chunks created from text")

            logger.info(f"[{document_id}] Created {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"[{document_id}] Chunking failed: {e}")
            raise RuntimeError(f"Chunking failed: {str(e)}")

        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="chunking",
            stage_progress=50
        )
        db.commit()

        # Stage 3: Embedding generation
        logger.info(f"[{document_id}] Stage 3: Embedding generation")
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="embedding",
            stage_progress=60
        )
        db.commit()

        try:
            # Get embedding provider
            embedding_provider = get_embedding_provider()

            # Extract text content from chunks
            chunk_texts = [chunk["content"] for chunk in chunks]

            # Generate embeddings in batches
            embeddings, total_tokens = embedding_provider.embed_batch(chunk_texts, batch_size=100)

            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")

            # Record token usage for embeddings
            token_repo = TokenUsageRepository(db)
            token_repo.record_usage(
                usage_type=TokenUsageTypeEnum.EMBEDDING,
                provider=embedding_provider.provider,
                model=embedding_provider.model,
                input_tokens=total_tokens,
                output_tokens=0,  # Embeddings don't have output tokens
                organisation_id=document.organisation_id,
                user_id=document.uploaded_by_id if hasattr(document, 'uploaded_by_id') else None,
                case_id=document.case_id,
                resource_type="document",
                resource_id=str(document_id)
            )

            logger.info(f"[{document_id}] Generated {len(embeddings)} embeddings using {total_tokens} tokens")

        except Exception as e:
            logger.error(f"[{document_id}] Embedding generation failed: {e}")
            raise RuntimeError(f"Embedding generation failed: {str(e)}")

        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="embedding",
            stage_progress=80
        )
        db.commit()

        # Stage 4: Vector indexing (save to database)
        logger.info(f"[{document_id}] Stage 4: Vector indexing")
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="indexing",
            stage_progress=85
        )
        db.commit()

        try:
            # Save DocumentChunk records with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                doc_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    embedding=embedding,  # pgvector handles the conversion
                    page_number=chunk.get("page_number", 1),
                    char_start=chunk.get("char_start"),
                    char_end=chunk.get("char_end")
                )
                db.add(doc_chunk)

            db.flush()
            logger.info(f"[{document_id}] Saved {len(chunks)} chunks to database")

        except Exception as e:
            logger.error(f"[{document_id}] Vector indexing failed: {e}")
            raise RuntimeError(f"Vector indexing failed: {str(e)}")

        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.PROCESSING,
            stage="indexing",
            stage_progress=95
        )
        db.commit()

        # Stage 5: Classification (optional - use first chunk for classification)
        logger.info(f"[{document_id}] Stage 5: Classification")
        try:
            # Use LLM to suggest document type based on content
            if chunks and len(chunks[0]["content"]) > 100:
                suggested_type = classify_document_content(chunks[0]["content"][:2000], document_id, db)
                if suggested_type:
                    # Store as metadata (don't overwrite user's classification)
                    if not document.metadata:
                        document.metadata = {}
                    document.metadata['suggested_type'] = suggested_type
                    db.flush()
                    logger.info(f"[{document_id}] Suggested type: {suggested_type}")
        except Exception as e:
            # Classification is optional, don't fail the job
            logger.warning(f"[{document_id}] Classification failed (non-critical): {e}")

        # Mark as completed
        doc_repo.update_status(
            document_id=document_id,
            overall_status=DocumentStatusEnum.COMPLETED,
            stage="completed",
            stage_progress=100
        )
        db.commit()

        logger.info(f"[{document_id}] Processing completed successfully: {len(chunks)} chunks indexed")

        # TODO: Emit event for notifications
        # emit_event('document.completed', document_id=document_id)

    except Exception as e:
        logger.error(f"[{document_id}] Processing failed: {e}", exc_info=True)

        if db:
            try:
                doc_repo = DocumentRepository(db)
                doc_repo.update_status(
                    document_id=document_id,
                    overall_status=DocumentStatusEnum.FAILED,
                    stage="failed",
                    stage_progress=0,
                    error_message=str(e)
                )
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

        raise  # Re-raise for RQ retry logic

    finally:
        if db:
            db.close()


def classify_document_content(text_sample: str, document_id: str, db: Session) -> Optional[str]:
    """
    Classify document type using LLM with token usage tracking.

    Args:
        text_sample: First ~2000 chars of document
        document_id: Document ID for token attribution
        db: Database session for recording usage

    Returns:
        Suggested document type or None if classification fails
    """
    try:
        llm_provider = get_llm_provider()

        prompt = f"""Analyze this legal document excerpt and classify its type.

Document excerpt:
{text_sample}

Classify as one of:
- pleading (court filing, claim, plea, replication)
- affidavit (sworn statement, deponent)
- correspondence (letter, email)
- contract (agreement, terms)
- evidence (exhibit, record)
- court_order (judgment, ruling, order)
- other

Respond with just the category name, nothing else."""

        generation_result = llm_provider.generate(
            prompt=prompt,
            system_message="You are a legal document classification assistant. Respond with only the category name.",
            temperature=0.3,  # Low temperature for consistent classification
            max_tokens=50
        )

        # Record token usage
        doc_repo = DocumentRepository(db)
        document = doc_repo.get_by_id(document_id)
        if document:
            token_repo = TokenUsageRepository(db)
            token_repo.record_usage(
                usage_type=TokenUsageTypeEnum.LLM_GENERATION,
                provider=llm_provider.provider,
                model=generation_result.model,
                input_tokens=generation_result.input_tokens,
                output_tokens=generation_result.output_tokens,
                organisation_id=document.organisation_id,
                user_id=document.uploaded_by_id if hasattr(document, 'uploaded_by_id') else None,
                case_id=document.case_id,
                resource_type="document",
                resource_id=str(document_id)
            )

        # Extract category from response
        category = generation_result.content.strip().lower()
        valid_categories = ["pleading", "affidavit", "correspondence", "contract", "evidence", "court_order", "other"]

        if category in valid_categories:
            return category

        return None

    except Exception as e:
        logger.warning(f"Document classification failed: {e}")
        return None
