"""
Document Analysis Service

Analyzes case documents to extract key facts, parties, dates, and warnings.
Used by the Document Assistant chatbot to provide intelligent case summaries.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import re
import json

from app.persistence.models import Case, Document, DocumentChunk, Rulebook
from app.core.ai_providers import get_llm_provider


class DocumentAnalysisService:
    """
    Analyze case documents to extract key facts, parties, dates.
    """

    # Simple cache for analysis results (case_id -> analysis result)
    # In production, use Redis or similar
    _analysis_cache: Dict[str, tuple[datetime, Dict[str, Any]]] = {}
    _cache_duration_minutes = 60

    @staticmethod
    def analyze_case_documents(
        case_id: str,
        db: Session,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Analyze all completed documents in a case.

        Args:
            case_id: UUID of the case
            db: Database session
            analysis_type: "full" | "summary" | "key_facts"

        Returns:
            Dictionary with:
            - key_parties: List of parties mentioned
            - important_dates: Timeline of events
            - key_facts: Factual statements with sources
            - warnings: Potential issues (missing signatures, etc.)
            - document_types: Count by type
            - total_documents: Total document count
            - completed_documents: Successfully processed count
        """
        # Check cache first
        cache_key = f"{case_id}:{analysis_type}"
        if cache_key in DocumentAnalysisService._analysis_cache:
            cached_time, cached_result = DocumentAnalysisService._analysis_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(minutes=DocumentAnalysisService._cache_duration_minutes):
                return cached_result

        # Get all documents for this case
        documents = db.query(Document).filter(
            Document.case_id == case_id
        ).all()

        total_documents = len(documents)
        completed_documents = [d for d in documents if d.overall_status == 'completed']
        processing_documents = [d for d in documents if d.overall_status == 'processing']

        if not completed_documents:
            return {
                "case_id": case_id,
                "total_documents": total_documents,
                "completed_documents": 0,
                "processing_documents": len(processing_documents),
                "analysis": {
                    "key_parties": [],
                    "important_dates": [],
                    "key_facts": [],
                    "document_types": {},
                    "warnings": []
                },
                "message": "No completed documents to analyze yet."
            }

        # Build context from document chunks
        context_parts = []
        document_metadata = []

        for doc in completed_documents[:10]:  # Limit to first 10 docs to avoid token limits
            # Get top chunks for this document
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).order_by(DocumentChunk.page_number, DocumentChunk.id).limit(20).all()

            if chunks:
                doc_text = "\n".join([chunk.text_content for chunk in chunks])
                context_parts.append(f"### {doc.filename}\n{doc_text[:2000]}")  # Limit per doc
                document_metadata.append({
                    "filename": doc.filename,
                    "document_type": doc.document_type,
                    "pages": doc.pages
                })

        # Create analysis prompt
        if analysis_type == "summary":
            analysis_prompt = DocumentAnalysisService._create_summary_prompt(
                context_parts, document_metadata
            )
        elif analysis_type == "key_facts":
            analysis_prompt = DocumentAnalysisService._create_key_facts_prompt(
                context_parts, document_metadata
            )
        else:  # full
            analysis_prompt = DocumentAnalysisService._create_full_analysis_prompt(
                context_parts, document_metadata
            )

        # Call LLM to extract structured information
        llm_provider = get_llm_provider()

        # Use generate_with_tools to get response (or just generate for simple case)
        system_msg = "You are a legal document analyzer for South African litigation. Extract information accurately and cite sources."
        result = llm_provider.generate(
            prompt=analysis_prompt,
            system_message=system_msg,
            temperature=0.3,  # Lower temperature for factual extraction
            max_tokens=2000
        )

        response = {"content": result.content, "usage": {"total_tokens": result.input_tokens + result.output_tokens}}

        # Parse the structured response
        try:
            analysis_result = json.loads(response["content"])
        except json.JSONDecodeError:
            # Fallback: create basic structure
            analysis_result = {
                "key_parties": [],
                "important_dates": [],
                "key_facts": [],
                "document_types": {},
                "warnings": []
            }

        # Add document type counts
        doc_type_counts = {}
        for doc in completed_documents:
            doc_type = doc.document_type or "unknown"
            doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

        result = {
            "case_id": case_id,
            "total_documents": total_documents,
            "completed_documents": len(completed_documents),
            "processing_documents": len(processing_documents),
            "analysis": {
                **analysis_result,
                "document_types": doc_type_counts
            },
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "cost_usd": response.get("cost", 0.0)
        }

        # Cache the result
        DocumentAnalysisService._analysis_cache[cache_key] = (datetime.utcnow(), result)

        return result

    @staticmethod
    def _create_full_analysis_prompt(context_parts: List[str], metadata: List[Dict]) -> str:
        """Create prompt for full document analysis."""
        context = "\n\n".join(context_parts)
        doc_list = ", ".join([m["filename"] for m in metadata])

        return f"""Analyze these legal documents from a South African litigation case and extract key information.

Documents: {doc_list}

Content:
{context}

Extract and return a JSON object with this exact structure:
{{
  "key_parties": [
    {{"name": "Party Name", "role": "Plaintiff/Defendant/Witness/etc", "mentioned_in": ["doc1.pdf", "doc2.pdf"]}}
  ],
  "important_dates": [
    {{"date": "YYYY-MM-DD", "description": "Event description", "source": "filename.pdf", "page": 1}}
  ],
  "key_facts": [
    {{"fact": "Factual statement", "confidence": 0.95, "source": "filename.pdf", "page": 1}}
  ],
  "warnings": [
    {{"type": "missing_signature|incomplete|unclear", "message": "Description", "severity": "high|medium|low"}}
  ]
}}

Guidelines:
- Only extract facts explicitly stated in documents
- Use actual dates in YYYY-MM-DD format
- Cite source document and page number
- Confidence: 1.0 = certain, 0.5 = uncertain
- Flag potential issues in warnings
"""

    @staticmethod
    def _create_summary_prompt(context_parts: List[str], metadata: List[Dict]) -> str:
        """Create prompt for brief summary analysis."""
        context = "\n\n".join(context_parts)
        doc_list = ", ".join([m["filename"] for m in metadata])

        return f"""Provide a brief summary of these legal documents.

Documents: {doc_list}

Content:
{context}

Extract and return a JSON object with:
{{
  "key_parties": [{{"name": "Name", "role": "Role"}}],
  "important_dates": [{{"date": "YYYY-MM-DD", "description": "Description"}}],
  "key_facts": [{{"fact": "Statement", "source": "filename.pdf"}}]
}}

Keep it concise - top 3 parties, top 3 dates, top 5 facts.
"""

    @staticmethod
    def _create_key_facts_prompt(context_parts: List[str], metadata: List[Dict]) -> str:
        """Create prompt for key facts only."""
        context = "\n\n".join(context_parts)

        return f"""Extract only the most critical facts from these documents.

{context}

Return JSON:
{{
  "key_facts": [{{"fact": "Statement", "confidence": 0.95, "source": "filename.pdf", "page": 1}}]
}}

Focus on facts that would be important for legal proceedings.
"""

    @staticmethod
    def generate_document_summary(
        documents: List[Document],
        db: Session
    ) -> str:
        """
        Generate a brief summary of all documents for welcome message.

        Args:
            documents: List of documents in the case
            db: Database session

        Returns:
            Human-readable summary string
        """
        if not documents:
            return "No documents uploaded yet."

        completed = [d for d in documents if d.overall_status == 'completed']
        processing = [d for d in documents if d.overall_status == 'processing']
        failed = [d for d in documents if d.overall_status == 'failed']

        summary_parts = []

        if completed:
            summary_parts.append(f"{len(completed)} document(s) processed and ready")
        if processing:
            summary_parts.append(f"{len(processing)} still processing")
        if failed:
            summary_parts.append(f"{len(failed)} failed (can be retried)")

        return ", ".join(summary_parts)

    @staticmethod
    def validate_draft_readiness(
        case_id: str,
        rulebook_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Check if case has sufficient documents to start a draft.

        Args:
            case_id: UUID of the case
            rulebook_id: ID of the rulebook to check against
            db: Database session

        Returns:
            Dictionary with:
            - ready: bool
            - missing_requirements: List[str]
            - recommendations: List[str]
        """
        # Get completed documents
        completed_docs = db.query(Document).filter(
            and_(
                Document.case_id == case_id,
                Document.overall_status == 'completed'
            )
        ).count()

        # Get rulebook if exists
        rulebook = db.query(Rulebook).filter(Rulebook.id == rulebook_id).first()

        missing = []
        recommendations = []

        # Basic check: at least one completed document
        if completed_docs == 0:
            missing.append("At least one completed document required")
            recommendations.append("Upload and process case documents before drafting")
            return {
                "ready": False,
                "missing_requirements": missing,
                "recommendations": recommendations
            }

        # Check rulebook requirements if available
        if rulebook and rulebook.rules_json:
            # Could add specific checks based on rulebook requirements
            # For now, just check basic completion
            pass

        # Recommendation for more documents
        if completed_docs < 3:
            recommendations.append("Consider uploading more supporting documents for better draft quality")

        return {
            "ready": True,
            "missing_requirements": [],
            "recommendations": recommendations
        }

    @staticmethod
    def clear_cache(case_id: Optional[str] = None):
        """
        Clear analysis cache for a case or all cases.

        Args:
            case_id: If provided, clear only this case. Otherwise clear all.
        """
        if case_id:
            keys_to_remove = [k for k in DocumentAnalysisService._analysis_cache.keys() if k.startswith(case_id)]
            for key in keys_to_remove:
                del DocumentAnalysisService._analysis_cache[key]
        else:
            DocumentAnalysisService._analysis_cache.clear()
