-- Migration: Add pgvector HNSW indexes for performance optimization
-- Phase 3.5 - Vector search performance optimization
--
-- Background:
-- pgvector supports two index types for approximate nearest neighbor search:
-- 1. HNSW (Hierarchical Navigable Small World) - Better for high recall, faster build
-- 2. IVFFlat (Inverted File with Flat compression) - Better for large datasets
--
-- We use HNSW for better query performance with our expected dataset size (< 1M vectors)
--
-- Performance impact:
-- - Without index: ~100-500ms for similarity search
-- - With HNSW index: ~5-20ms for similarity search
--
-- References:
-- - https://github.com/pgvector/pgvector#hnsw
-- - Development Guidelines: "Use HNSW or IVF for vector similarity"

-- ============================================================================
-- Step 1: Create HNSW index on document_chunk embeddings
-- ============================================================================

-- HNSW index for cosine distance (our primary similarity metric)
-- m = 16: Number of connections per layer (default, good balance)
-- ef_construction = 64: Size of dynamic candidate list during construction (default)
CREATE INDEX IF NOT EXISTS idx_document_chunk_embedding_hnsw_cosine
ON document_chunk
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Alternative: L2 distance index (if needed for different similarity metrics)
-- Commented out by default - only create if L2 distance is required
-- CREATE INDEX IF NOT EXISTS idx_document_chunk_embedding_hnsw_l2
-- ON document_chunk
-- USING hnsw (embedding vector_l2_ops)
-- WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Step 2: Add composite indexes for filtered vector searches
-- ============================================================================

-- Our search queries typically filter by:
-- 1. document_id (for single-document search)
-- 2. Document.case_id (for case-wide search)
-- 3. Document.overall_status = 'completed' (only search processed documents)
-- 4. Document.document_type (optional filter)

-- Add index on document_id for chunk lookup
-- This supports queries like: "search within this specific document"
CREATE INDEX IF NOT EXISTS idx_document_chunk_document_id
ON document_chunk (document_id);

-- Add index on chunk_index for deduplication
-- Used during draft research to avoid duplicate chunks
CREATE INDEX IF NOT EXISTS idx_document_chunk_document_chunk
ON document_chunk (document_id, chunk_index);

-- ============================================================================
-- Step 3: Optimize document table for vector search joins
-- ============================================================================

-- Composite index for case + status filtering
-- Supports queries: "search all completed documents in this case"
CREATE INDEX IF NOT EXISTS idx_document_case_status
ON document (case_id, overall_status)
WHERE overall_status = 'completed';

-- Add document_type to support filtered searches
-- Supports queries: "search only pleadings in this case"
CREATE INDEX IF NOT EXISTS idx_document_case_status_type
ON document (case_id, overall_status, document_type)
WHERE overall_status = 'completed';

-- ============================================================================
-- Step 4: Statistics and maintenance
-- ============================================================================

-- Update table statistics for query planner
ANALYZE document_chunk;
ANALYZE document;

-- ============================================================================
-- Performance tuning parameters (optional - set at session or database level)
-- ============================================================================

-- Set search quality parameter (higher = better recall, slower search)
-- Default: 40
-- Recommended range: 40-200
-- This can be set per-query in application code:
-- SET LOCAL hnsw.ef_search = 100;

-- Example usage in application:
-- db.execute(text("SET LOCAL hnsw.ef_search = 100"))
-- results = db.execute(vector_search_query).all()

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Check index creation status
-- SELECT schemaname, tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename IN ('document_chunk', 'document')
-- ORDER BY tablename, indexname;

-- Check index usage statistics (after some queries)
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan as index_scans,
--     idx_tup_read as tuples_read,
--     idx_tup_fetch as tuples_fetched
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public' AND tablename IN ('document_chunk', 'document')
-- ORDER BY tablename, indexname;

-- Estimate index size
-- SELECT
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public' AND tablename IN ('document_chunk', 'document')
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

-- DROP INDEX IF EXISTS idx_document_chunk_embedding_hnsw_cosine;
-- DROP INDEX IF EXISTS idx_document_chunk_document_id;
-- DROP INDEX IF EXISTS idx_document_chunk_document_chunk;
-- DROP INDEX IF EXISTS idx_document_case_status;
-- DROP INDEX IF EXISTS idx_document_case_status_type;
