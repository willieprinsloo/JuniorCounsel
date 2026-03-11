# Phase 3 Implementation Checklist

**Status:** Ready to Start
**Duration:** 3-4 weeks (28 days)
**Start Date:** TBD
**Completion Target:** TBD

---

## Pre-Implementation Setup

### Environment Requirements
- [ ] **Tesseract OCR installed** (`brew install tesseract` or `apt install tesseract-ocr`)
- [ ] **Poppler installed** (`brew install poppler` or `apt install poppler-utils`)
- [ ] **OpenAI API key configured** in `.env` (`OPENAI_API_KEY=sk-...`)
- [ ] **Anthropic API key configured** in `.env` (optional: `ANTHROPIC_API_KEY=sk-ant-...`)
- [ ] **Redis running** (`redis-server` or `brew services start redis`)
- [ ] **PostgreSQL with pgvector running**
- [ ] **Workers running** (`python run_workers.py`)

### Python Dependencies
- [ ] Update `requirements.txt` with Phase 3 dependencies:
  ```txt
  # AI/ML
  openai==1.12.0
  anthropic==0.18.0

  # OCR
  pytesseract==0.3.10
  pillow==10.2.0
  pdf2image==1.17.0

  # Text extraction
  pypdf==4.0.0
  python-docx==1.1.0
  ```
- [ ] Run `pip install -r requirements.txt`

### Configuration
- [ ] Add to `.env`:
  ```bash
  # AI Providers
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...  # Optional

  # Embedding Configuration
  EMBEDDING_PROVIDER=openai
  EMBEDDING_MODEL=text-embedding-3-small

  # LLM Configuration
  LLM_PROVIDER=openai
  LLM_MODEL=gpt-4-turbo
  ```
- [ ] Update `.env.example` with Phase 3 variables

---

## Phase 3.1 - AI Provider Setup (Days 1-2)

### Day 1: OpenAI Integration

**File:** `src/app/core/ai_providers.py`

#### Tasks
- [ ] Create `EmbeddingProvider` class
  - [ ] Support OpenAI `text-embedding-3-small` model
  - [ ] Implement `embed_text(text: str) -> List[float]` method
  - [ ] Implement `embed_batch(texts: List[str]) -> List[List[float]]` method
  - [ ] Handle API errors gracefully (rate limits, invalid API key)
  - [ ] Add batch size limit (100 texts per call)

- [ ] Create `LLMProvider` class
  - [ ] Support OpenAI `gpt-4-turbo` model
  - [ ] Support Anthropic `claude-3-opus` model (optional)
  - [ ] Implement `generate(prompt, system_message, temperature, max_tokens) -> str`
  - [ ] Handle API errors and rate limits
  - [ ] Add retry logic with exponential backoff

- [ ] Create global provider instances
  - [ ] `embedding_provider = EmbeddingProvider()`
  - [ ] `llm_provider = LLMProvider()`

#### Acceptance Criteria
- [ ] Can generate embedding for single text (1536 dimensions)
- [ ] Can generate embeddings for batch of 100 texts
- [ ] Can generate LLM response with OpenAI
- [ ] API errors are caught and logged appropriately
- [ ] Unit tests pass for both providers

#### Testing Commands
```python
# Test embedding
from app.core.ai_providers import embedding_provider
embedding = embedding_provider.embed_text("Test contract clause")
assert len(embedding) == 1536
print("✅ Embedding generation works")

# Test LLM
from app.core.ai_providers import llm_provider
response = llm_provider.generate("What is the capital of South Africa?")
assert len(response) > 0
print("✅ LLM generation works")
```

---

## Phase 3.2 - Document Processing Implementation (Days 2-10)

### Day 2-3: OCR Implementation

**File:** `src/app/workers/ocr.py`

#### Tasks
- [ ] Create `perform_ocr(file_path: str) -> Dict` function
  - [ ] Support PDF files (convert to images first)
  - [ ] Support image files (JPG, PNG, TIFF)
  - [ ] Return text, confidence score, page count
  - [ ] Handle multi-page PDFs

- [ ] Create `_ocr_pdf(pdf_path: str) -> Dict` helper
  - [ ] Convert PDF to images at 300 DPI
  - [ ] OCR each page with pytesseract
  - [ ] Calculate average confidence score
  - [ ] Combine all page text

- [ ] Create `_ocr_image(image_path: str) -> Dict` helper
  - [ ] Open image with PIL
  - [ ] Run pytesseract OCR
  - [ ] Extract text and confidence

#### Acceptance Criteria
- [ ] Can OCR a single-page PDF (confidence > 80%)
- [ ] Can OCR a multi-page PDF (all pages processed)
- [ ] Can OCR JPEG/PNG images
- [ ] Returns structured result with text, confidence, page_count
- [ ] Handles corrupted/unreadable files gracefully
- [ ] Unit tests pass with sample documents

#### Testing Commands
```python
from app.workers.ocr import perform_ocr
result = perform_ocr("tests/fixtures/sample_scanned.pdf")
assert result["confidence"] > 70
assert result["page_count"] > 0
print(f"✅ OCR works: {result['confidence']}% confidence, {result['page_count']} pages")
```

---

### Day 4-5: Text Extraction

**File:** `src/app/workers/text_extraction.py`

#### Tasks
- [ ] Create `extract_text_from_pdf(pdf_path: str) -> str` function
  - [ ] Use pypdf to extract text
  - [ ] Add page markers `[Page N]`
  - [ ] Handle PDFs without text layer

- [ ] Create `extract_text_from_docx(docx_path: str) -> str` function
  - [ ] Use python-docx to extract paragraphs
  - [ ] Preserve paragraph structure

- [ ] Create `extract_text(file_path: str, needs_ocr: bool) -> str` router function
  - [ ] Route to OCR if needs_ocr=True
  - [ ] Route to pypdf for text-based PDFs
  - [ ] Route to python-docx for DOCX files
  - [ ] Raise error for unsupported file types

- [ ] Create `has_text_layer(pdf_path: str) -> bool` utility
  - [ ] Check if PDF has extractable text
  - [ ] Return True if first page has >50 chars

#### Acceptance Criteria
- [ ] Can extract text from text-based PDF
- [ ] Can extract text from DOCX
- [ ] Routes to OCR for scanned PDFs
- [ ] Page numbers are preserved in output
- [ ] Handles empty documents gracefully
- [ ] Unit tests pass with various file types

#### Testing Commands
```python
from app.workers.text_extraction import extract_text, has_text_layer

# Test text-based PDF
text = extract_text("tests/fixtures/contract.pdf", needs_ocr=False)
assert "[Page 1]" in text
print(f"✅ Text extraction works: {len(text)} chars")

# Test has_text_layer
has_text = has_text_layer("tests/fixtures/contract.pdf")
assert has_text == True
print("✅ Text layer detection works")
```

---

### Day 6-7: Text Chunking

**File:** `src/app/workers/chunking.py`

#### Tasks
- [ ] Create `chunk_text(text, chunk_size, chunk_overlap, min_chunk_size) -> List[Dict]` function
  - [ ] Split by paragraphs (double newlines)
  - [ ] Combine small paragraphs
  - [ ] Split large paragraphs if needed
  - [ ] Add overlap between chunks (50 chars default)
  - [ ] Skip chunks smaller than min_chunk_size (100 chars default)
  - [ ] Return chunks with metadata (chunk_index, char_start, char_end)

- [ ] Create `extract_page_number(chunk_text: str) -> int` utility
  - [ ] Extract page number from `[Page N]` marker
  - [ ] Return 1 if no marker found

#### Acceptance Criteria
- [ ] Can chunk a 10-page document (produces 20-50 chunks)
- [ ] Chunks are 100-2048 characters each
- [ ] Chunks have overlap for context continuity
- [ ] Page numbers are correctly extracted
- [ ] Chunk metadata includes char_start and char_end
- [ ] Unit tests pass with various document sizes

#### Testing Commands
```python
from app.workers.chunking import chunk_text, extract_page_number

text = "This is a test document.\n\n[Page 1]\nFirst paragraph...\n\n[Page 2]\nSecond paragraph..."
chunks = chunk_text(text, chunk_size=512, chunk_overlap=50)

assert len(chunks) > 0
assert chunks[0]["chunk_index"] == 0
assert "content" in chunks[0]
print(f"✅ Chunking works: {len(chunks)} chunks generated")

page_num = extract_page_number("[Page 5]\nSome text")
assert page_num == 5
print("✅ Page extraction works")
```

---

### Day 8-10: Embedding & Indexing

**File:** `src/app/workers/document_processing.py` (update)

#### Tasks
- [ ] Replace placeholder `perform_ocr` with actual implementation
  - [ ] Import from `app.workers.ocr`
  - [ ] Call `perform_ocr(file_path)`
  - [ ] Store OCR confidence in document metadata

- [ ] Replace placeholder `extract_text_from_pdf` with actual implementation
  - [ ] Import from `app.workers.text_extraction`
  - [ ] Call `extract_text(file_path, needs_ocr)`

- [ ] Replace placeholder `chunk_text` with actual implementation
  - [ ] Import from `app.workers.chunking`
  - [ ] Call `chunk_text(text, chunk_size=512)`

- [ ] Replace placeholder `generate_embeddings` with actual implementation
  - [ ] Import `embedding_provider` from `app.core.ai_providers`
  - [ ] Extract text content from chunks
  - [ ] Call `embedding_provider.embed_batch(texts, batch_size=100)`
  - [ ] Handle API errors and retry

- [ ] Implement `save_document_chunks` function
  - [ ] Create `DocumentChunk` records
  - [ ] Set document_id, chunk_index, content, embedding
  - [ ] Set page_number, char_start, char_end
  - [ ] Bulk insert to database

- [ ] Update status tracking
  - [ ] Set stage to "ocr", "text_extraction", "chunking", "embedding", "indexing"
  - [ ] Update stage_progress (0-30%, 30-50%, 50-70%, 70-85%, 85-100%)
  - [ ] Handle errors and set status to "failed"

#### Acceptance Criteria
- [ ] Can process a PDF end-to-end (upload → completed)
- [ ] All 6 stages execute correctly (OCR, text, chunk, embed, index, classify)
- [ ] DocumentChunk records are created with embeddings
- [ ] Status updates are visible in real-time
- [ ] Failed documents have error_message set
- [ ] Integration test passes (upload → search)

#### Testing Commands
```bash
# 1. Upload a test document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer {token}" \
  -F "file=@tests/fixtures/sample_contract.pdf" \
  -F "case_id={case_uuid}"

# Response: {"id": "doc-uuid", "overall_status": "queued", ...}

# 2. Monitor worker logs
tail -f logs/worker.log
# Should see: OCR → Text extraction → Chunking → Embedding → Indexing

# 3. Check document status
curl http://localhost:8000/api/v1/documents/{doc_id} \
  -H "Authorization: Bearer {token}"

# Expected: {"overall_status": "completed", "stage": "completed", "stage_progress": 100}

# 4. Verify chunks were created
psql junior_counsel_dev -c "SELECT COUNT(*) FROM document_chunks WHERE document_id = '{doc_id}';"
# Expected: 10-50 chunks depending on document size
```

---

## Phase 3.3 - Vector Search & RAG (Days 11-17)

### Day 11-13: Vector Search Implementation

**File:** `src/app/api/v1/search.py`

#### Tasks
- [ ] Create search router (`router = APIRouter()`)

- [ ] Implement `GET /api/v1/search/` endpoint
  - [ ] Accept query parameters: case_id, query, limit, similarity_threshold, document_type
  - [ ] Generate query embedding with `embedding_provider.embed_text(query)`
  - [ ] Build pgvector search query
  - [ ] Use `func.cosine_distance(DocumentChunk.embedding, query_embedding)`
  - [ ] Join with Document table for metadata
  - [ ] Filter by case_id (required)
  - [ ] Filter by document_type (optional)
  - [ ] Order by distance (ascending = most similar first)
  - [ ] Limit results
  - [ ] Convert distance to similarity score (1 - distance)
  - [ ] Filter by similarity_threshold
  - [ ] Return results with citations

- [ ] Register router in `main.py`
  - [ ] `app.include_router(search.router, prefix="/api/v1/search", tags=["search"])`

#### Acceptance Criteria
- [ ] Can search within a case's documents
- [ ] Returns relevant chunks sorted by similarity
- [ ] Similarity scores are accurate (0-1 range)
- [ ] Filters by document_type work correctly
- [ ] Search query takes < 2 seconds
- [ ] Results include citations (document, page, chunk_index)
- [ ] Unit tests pass for search endpoint

#### Testing Commands
```bash
# Search for "payment terms" in case documents
curl "http://localhost:8000/api/v1/search/?case_id={case_uuid}&query=payment+terms&limit=10" \
  -H "Authorization: Bearer {token}"

# Expected response:
{
  "query": "payment terms",
  "results": [
    {
      "chunk_id": "chunk-uuid",
      "document_id": "doc-uuid",
      "document_filename": "contract.pdf",
      "content": "Payment shall be made within 30 days...",
      "page_number": 5,
      "similarity": 0.92,
      "citation": {
        "document": "contract.pdf",
        "page": 5,
        "chunk_index": 12
      }
    }
  ],
  "total": 1
}
```

---

### Day 14-17: Q&A with RAG

**File:** `src/app/api/v1/qa.py`

#### Tasks
- [ ] Create Q&A router (`router = APIRouter()`)

- [ ] Create `QARequest` Pydantic schema
  - [ ] case_id: str
  - [ ] question: str
  - [ ] max_context_chunks: int = 5

- [ ] Create `QAResponse` Pydantic schema
  - [ ] question: str
  - [ ] answer: str
  - [ ] citations: List[dict]
  - [ ] context_used: int

- [ ] Implement `POST /api/v1/qa/` endpoint
  - [ ] Call `search_documents()` to get relevant chunks
  - [ ] Raise 404 if no results found
  - [ ] Build context from top chunks with citation markers [1], [2], etc.
  - [ ] Build LLM prompt with context and question
  - [ ] Set system message with legal assistant instructions
  - [ ] Call `llm_provider.generate()` with temperature=0.3 (factual accuracy)
  - [ ] Return answer with citations

- [ ] Register router in `main.py`
  - [ ] `app.include_router(qa.router, prefix="/api/v1/qa", tags=["qa"])`

#### Acceptance Criteria
- [ ] Can answer questions based on case documents
- [ ] Answers include citation markers [1], [2], etc.
- [ ] Citations are returned with metadata (document, page, similarity)
- [ ] Returns 404 if no relevant documents found
- [ ] LLM responses are factually accurate (based on context)
- [ ] Response time < 8 seconds
- [ ] Integration tests pass

#### Testing Commands
```bash
# Ask a question about uploaded documents
curl -X POST http://localhost:8000/api/v1/qa/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "{case_uuid}",
    "question": "What are the payment terms in the contract?",
    "max_context_chunks": 5
  }'

# Expected response:
{
  "question": "What are the payment terms in the contract?",
  "answer": "According to the contract [1], payment is due within 30 days of invoice. Late payments incur a 1.5% monthly interest charge [2].",
  "citations": [
    {"id": "[1]", "document": "contract.pdf", "page": 5, "similarity": 0.92},
    {"id": "[2]", "document": "contract.pdf", "page": 5, "similarity": 0.87}
  ],
  "context_used": 2
}
```

---

## Phase 3.4 - Draft Generation (Days 18-24)

### Day 18-21: Draft Research Worker

**File:** `src/app/workers/draft_generation.py` (update)

#### Tasks
- [ ] Replace placeholder `draft_research_job` with actual implementation
  - [ ] Get DraftSession from database
  - [ ] Get Rulebook from database
  - [ ] Update status to DraftSessionStatusEnum.RESEARCH
  - [ ] Extract search queries from intake_responses
  - [ ] Loop through queries and perform vector search
  - [ ] Collect relevant excerpts (similarity > 0.7)
  - [ ] Build research_summary JSON with:
    - [ ] queries_executed
    - [ ] total_excerpts
    - [ ] relevant_documents
    - [ ] key_excerpts (top 20)
    - [ ] generated_at timestamp
  - [ ] Save research_summary to DraftSession
  - [ ] Update status to DraftSessionStatusEnum.DRAFTING
  - [ ] Auto-enqueue `draft_generation_job`

- [ ] Implement `extract_search_queries(intake_responses, rulebook_rules) -> List[str]`
  - [ ] Extract key facts from intake_responses (strings > 20 chars)
  - [ ] Add rulebook-specific queries if defined
  - [ ] Limit to 10 queries total

#### Acceptance Criteria
- [ ] Can perform RAG research for draft session
- [ ] Extracts 3-10 search queries from intake responses
- [ ] Finds 5-50 relevant excerpts
- [ ] research_summary contains all required fields
- [ ] Auto-triggers draft generation job
- [ ] Status updates correctly (research → drafting)
- [ ] Worker logs show progress

#### Testing Commands
```bash
# 1. Create a draft session
curl -X POST http://localhost:8000/api/v1/draft-sessions/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "{case_uuid}",
    "rulebook_id": "{rulebook_id}",
    "document_type": "affidavit",
    "title": "Test Affidavit",
    "intake_responses": {
      "deponent_name": "John Doe",
      "facts": "On 1 January 2024, the defendant breached the payment terms by failing to pay R50,000 within 30 days."
    }
  }'

# Response: {"id": "draft-uuid", "status": "pending", ...}

# 2. Trigger research job
curl -X POST http://localhost:8000/api/v1/draft-sessions/{draft_id}/start \
  -H "Authorization: Bearer {token}"

# 3. Monitor worker logs
tail -f logs/worker.log
# Should see: "Starting research for draft {draft_id}"

# 4. Check draft status
curl http://localhost:8000/api/v1/draft-sessions/{draft_id} \
  -H "Authorization: Bearer {token}"

# Expected: {"status": "drafting", "research_summary": {...}}
```

---

### Day 22-24: Draft Generation Worker

**File:** `src/app/workers/draft_generation.py` (update)

#### Tasks
- [ ] Replace placeholder `draft_generation_job` with actual implementation
  - [ ] Get DraftSession and Rulebook from database
  - [ ] Verify status is DraftSessionStatusEnum.DRAFTING
  - [ ] Build drafting prompt with:
    - [ ] Document structure from rulebook
    - [ ] Intake responses
    - [ ] Research excerpts with citations
    - [ ] Instructions for legal drafting
  - [ ] Get system message for document type
  - [ ] Call `llm_provider.generate()` with temperature=0.5
  - [ ] Extract citations from generated content (find [1], [2], etc.)
  - [ ] Map citations to research excerpts
  - [ ] Save generated_content and citations to DraftSession
  - [ ] Update status to DraftSessionStatusEnum.REVIEW
  - [ ] Log completion

- [ ] Implement `build_drafting_prompt(rulebook, intake_responses, research_summary, document_type) -> str`
  - [ ] Format document structure from rulebook
  - [ ] Format intake responses as bullet list
  - [ ] Format research excerpts with [N] markers
  - [ ] Add drafting instructions
  - [ ] Return complete prompt

- [ ] Implement `get_system_message_for_document_type(document_type: str) -> str`
  - [ ] Define system messages for:
    - [ ] affidavit
    - [ ] pleading
    - [ ] heads_of_argument
  - [ ] Return default message for other types

- [ ] Implement `extract_citations_from_content(content: str, research_summary: dict) -> List[dict]`
  - [ ] Find all [N] citation markers in content
  - [ ] Map to research excerpts by index
  - [ ] Return list of citations with metadata

- [ ] Implement `format_document_structure(structure: List[dict]) -> str` utility
  - [ ] Convert rulebook structure to readable format
  - [ ] Include section names and requirements

#### Acceptance Criteria
- [ ] Can generate full draft document
- [ ] Draft follows rulebook structure
- [ ] Draft includes citations from research
- [ ] Citations are correctly mapped to source documents
- [ ] Draft is court-ready quality
- [ ] Status updates correctly (drafting → review)
- [ ] Generated content is saved to database
- [ ] Integration test passes (create draft → research → generate)

#### Testing Commands
```bash
# Wait for draft generation to complete (after research job)
# Check draft status periodically
while true; do
  curl http://localhost:8000/api/v1/draft-sessions/{draft_id} \
    -H "Authorization: Bearer {token}" | jq '.status'
  sleep 5
done

# Expected progression: pending → research → drafting → review

# Once status is "review", retrieve generated draft
curl http://localhost:8000/api/v1/draft-sessions/{draft_id} \
  -H "Authorization: Bearer {token}" | jq '.generated_content'

# Expected: Full draft document with citations like:
# "I, John Doe, make oath and state that:
#  1. I am the applicant in this matter.
#  2. On 1 January 2024, the defendant breached the payment terms [1]..."
```

---

## Phase 3.5 - Testing & Optimization (Days 25-28)

### Day 25-26: Integration Testing

**File:** `tests/integration/test_document_workflow.py`

#### Tasks
- [ ] Create integration test class `TestDocumentWorkflow`

- [ ] Implement `test_upload_and_process_pdf`
  - [ ] Upload test PDF via API
  - [ ] Wait for processing to complete (poll status)
  - [ ] Assert status is "completed"
  - [ ] Assert stage_progress is 100
  - [ ] Verify chunks were created in database

- [ ] Implement `test_search_after_processing`
  - [ ] Upload and process document
  - [ ] Perform vector search
  - [ ] Assert results are returned
  - [ ] Assert similarity scores > 0.7

- [ ] Implement `test_qa_with_citations`
  - [ ] Upload and process document
  - [ ] Ask question via Q&A endpoint
  - [ ] Assert answer is not empty
  - [ ] Assert citations are included
  - [ ] Assert citation markers [1], [2] in answer

**File:** `tests/integration/test_draft_workflow.py`

#### Tasks
- [ ] Create integration test class `TestDraftWorkflow`

- [ ] Implement `test_full_draft_workflow`
  - [ ] Upload case documents
  - [ ] Wait for processing
  - [ ] Create draft session with intake responses
  - [ ] Start draft research job
  - [ ] Wait for research to complete
  - [ ] Wait for generation to complete
  - [ ] Assert status is "review"
  - [ ] Assert generated_content is not empty
  - [ ] Assert citations are present

- [ ] Implement `test_draft_with_no_documents`
  - [ ] Create draft session without any case documents
  - [ ] Assert research fails with appropriate error

- [ ] Implement `test_draft_citation_accuracy`
  - [ ] Create draft with known documents
  - [ ] Verify citations point to correct source documents
  - [ ] Verify page numbers are accurate

#### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Test coverage > 80% for Phase 3 code
- [ ] Tests run in < 5 minutes
- [ ] Tests are reproducible (no flaky tests)
- [ ] Test fixtures are properly cleaned up

#### Testing Commands
```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ --cov=src/app --cov-report=term-missing

# Expected output:
# tests/integration/test_document_workflow.py::TestDocumentWorkflow::test_upload_and_process_pdf PASSED
# tests/integration/test_document_workflow.py::TestDocumentWorkflow::test_search_after_processing PASSED
# tests/integration/test_document_workflow.py::TestDocumentWorkflow::test_qa_with_citations PASSED
# tests/integration/test_draft_workflow.py::TestDraftWorkflow::test_full_draft_workflow PASSED
# ==================== 4 passed in 120.50s ====================
```

---

### Day 27-28: Performance Optimization

#### Database Optimization

**File:** SQL script or migration

#### Tasks
- [ ] Create pgvector HNSW index for fast similarity search
  ```sql
  CREATE INDEX document_chunks_embedding_idx
  ON document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```

- [ ] Create indexes on frequently queried columns
  ```sql
  CREATE INDEX idx_documents_case_id ON documents(case_id);
  CREATE INDEX idx_documents_status ON documents(overall_status);
  CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
  ```

- [ ] Analyze query performance
  ```sql
  EXPLAIN ANALYZE
  SELECT * FROM document_chunks
  ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
  LIMIT 10;
  ```

#### Embedding Performance

#### Tasks
- [ ] Verify batch embedding works (100 chunks per API call)
- [ ] Add embedding cache for repeated queries (Redis)
- [ ] Monitor OpenAI API quota usage
- [ ] Add retry logic with exponential backoff for API errors
- [ ] Log embedding generation time

#### LLM Performance

#### Tasks
- [ ] Optimize prompts to reduce token usage
- [ ] Implement streaming responses for better UX (future feature)
- [ ] Add fallback to faster models if quota exceeded
- [ ] Monitor LLM API usage and costs
- [ ] Log LLM generation time

#### Worker Performance

#### Tasks
- [ ] Monitor queue length with `rq info`
- [ ] Add worker health check endpoint
- [ ] Set appropriate job timeouts (30m for documents, 15m for drafts)
- [ ] Add job retry logic for transient failures
- [ ] Log worker performance metrics

#### Acceptance Criteria
- [ ] Vector search takes < 2 seconds (with 100K+ chunks)
- [ ] Q&A response time < 8 seconds
- [ ] Document processing < 5 minutes for 10-page doc
- [ ] Draft generation < 3 minutes
- [ ] Worker queue doesn't back up under load
- [ ] Database query performance is optimal (EXPLAIN ANALYZE shows index usage)
- [ ] Performance benchmarks documented

#### Testing Commands
```bash
# 1. Test search performance
time curl "http://localhost:8000/api/v1/search/?case_id={case_uuid}&query=payment+terms&limit=10" \
  -H "Authorization: Bearer {token}"
# Expected: < 2 seconds

# 2. Test Q&A performance
time curl -X POST http://localhost:8000/api/v1/qa/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "{case_uuid}", "question": "What are the payment terms?"}'
# Expected: < 8 seconds

# 3. Check queue status
rq info --url redis://localhost:6379/0
# Expected output:
# document_processing |███████████████████████████████████████| 0 / 0
# draft_generation    |███████████████████████████████████████| 0 / 0

# 4. Check database index usage
psql junior_counsel_dev -c "EXPLAIN ANALYZE SELECT * FROM document_chunks ORDER BY embedding <=> '[0.1,0.2,...]'::vector LIMIT 10;"
# Expected: "Index Scan using document_chunks_embedding_idx" in output
```

---

## Final Verification Checklist

### Feature Completeness
- [ ] Documents can be uploaded and fully processed (OCR → embedding → indexed)
- [ ] Vector search returns relevant document excerpts
- [ ] Q&A with citations works on case documents
- [ ] Draft generation produces court-ready content with citations
- [ ] Citation extraction and validation working
- [ ] All API endpoints documented in OpenAPI (Swagger)

### Performance Targets
- [ ] Document processing success rate > 95%
- [ ] OCR accuracy > 85% (confidence score)
- [ ] Search relevance (top-5 recall) > 80%
- [ ] Q&A citation accuracy > 90%
- [ ] Draft generation with 100% rulebook compliance
- [ ] End-to-end latency (upload → draft ready) < 5 minutes for 10-page doc
- [ ] Search query response time < 2 seconds
- [ ] Q&A response time < 8 seconds

### Code Quality
- [ ] All unit tests pass (pytest tests/unit/ -v)
- [ ] All integration tests pass (pytest tests/integration/ -v)
- [ ] Test coverage > 80% for Phase 3 code
- [ ] No linting errors (ruff check src/)
- [ ] No type errors (mypy src/)
- [ ] Code follows project conventions (see development_guidelines.md)

### Documentation
- [ ] API endpoints documented in API_Summary.md
- [ ] Phase 3 completion report created
- [ ] Known limitations documented
- [ ] Deployment requirements updated
- [ ] README updated with Phase 3 setup instructions

### Deployment Readiness
- [ ] .env.example updated with all Phase 3 variables
- [ ] requirements.txt includes all dependencies
- [ ] System dependencies documented (tesseract, poppler)
- [ ] Database indexes created
- [ ] Workers start successfully
- [ ] API health check passes
- [ ] OpenAPI docs accessible at /docs

---

## Success Criteria Summary

**Phase 3 is complete when:**

1. ✅ All 28 daily tasks are checked off
2. ✅ All integration tests pass
3. ✅ Performance targets are met
4. ✅ Documentation is complete
5. ✅ System is deployable

**Grade Target:** A (95/100)

**Next Phase:** Phase 4 - Frontend (Next.js + React + Tailwind CSS)

---

## Notes

- This checklist should be updated daily as tasks are completed
- Mark completed items with `[x]`
- Add notes for any blockers or issues encountered
- Estimated effort: 3-4 weeks for 1 developer

**Start Date:** TBD
**Estimated Completion:** TBD + 28 days
