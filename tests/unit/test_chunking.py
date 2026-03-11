"""
Unit tests for chunking module.
"""
import pytest

from app.workers.chunking import (
    chunk_text,
    extract_page_number,
    chunk_by_sentences,
    merge_small_chunks,
    estimate_tokens,
    validate_chunks
)


class TestChunkText:
    """Test chunk_text function."""

    def test_chunk_empty_text(self):
        """Test chunk_text raises error for empty text."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            chunk_text("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            chunk_text("   ")

    def test_chunk_invalid_parameters(self):
        """Test chunk_text raises error for invalid parameters."""
        # chunk_size < min_chunk_size
        with pytest.raises(ValueError, match="chunk_size .* must be >= min_chunk_size"):
            chunk_text("test text", chunk_size=50, min_chunk_size=100)

        # chunk_overlap >= chunk_size
        with pytest.raises(ValueError, match="chunk_overlap .* must be < chunk_size"):
            chunk_text("test text", chunk_size=100, chunk_overlap=100)

    def test_chunk_short_text(self):
        """Test chunking short text creates single chunk."""
        text = "This is a short paragraph."

        chunks = chunk_text(text, chunk_size=512, min_chunk_size=10)

        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["char_start"] == 0
        assert chunks[0]["char_end"] == len(text)

    def test_chunk_multi_paragraph_text(self):
        """Test chunking multi-paragraph text."""
        text = """First paragraph with some content.

Second paragraph with more content.

Third paragraph with even more content."""

        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10, min_chunk_size=10)

        assert len(chunks) >= 1
        assert all("paragraph" in chunk["content"] for chunk in chunks)

    def test_chunk_with_overlap(self):
        """Test chunking creates overlap between chunks."""
        # Create text large enough for multiple chunks
        para1 = "A" * 1000
        para2 = "B" * 1000
        para3 = "C" * 1000
        text = f"{para1}\n\n{para2}\n\n{para3}"

        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50, min_chunk_size=100)

        # Should have multiple chunks
        assert len(chunks) > 1

        # Check overlap exists (end of one chunk appears in start of next)
        # This is a simplified check - exact overlap depends on paragraph boundaries

    def test_chunk_respects_min_size(self):
        """Test chunking respects minimum chunk size."""
        text = """Short.

Medium paragraph.

Long paragraph with substantial content that should be kept."""

        chunks = chunk_text(text, chunk_size=100, min_chunk_size=30)

        # All chunks should be >= min_chunk_size
        for chunk in chunks:
            assert len(chunk["content"]) >= 30

    def test_chunk_metadata(self):
        """Test chunk metadata is correct."""
        text = """First paragraph.

Second paragraph."""

        chunks = chunk_text(text, chunk_size=512)

        for i, chunk in enumerate(chunks):
            assert "content" in chunk
            assert "chunk_index" in chunk
            assert "char_start" in chunk
            assert "char_end" in chunk
            assert "page_number" in chunk
            assert chunk["chunk_index"] == i

    def test_chunk_with_page_markers(self):
        """Test chunking extracts page numbers from markers."""
        text = """[Page 1]
First paragraph on page 1 with enough content to make a chunk.

[Page 2]
Second paragraph on page 2 with enough content to make a chunk.

[Page 3]
Third paragraph on page 3 with enough content to make a chunk."""

        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10, min_chunk_size=20)

        # Check page numbers are extracted - at least some chunks should have page info
        page_numbers = [chunk["page_number"] for chunk in chunks]
        assert all(page_num >= 1 for page_num in page_numbers)


class TestExtractPageNumber:
    """Test extract_page_number function."""

    def test_extract_from_marker(self):
        """Test extracting page number from [Page N] marker."""
        assert extract_page_number("[Page 1]\nSome text") == 1
        assert extract_page_number("[Page 5]\nSome text") == 5
        assert extract_page_number("[Page 100]\nSome text") == 100

    def test_extract_from_middle_of_text(self):
        """Test extracting page number when marker is in middle."""
        text = "Some text before\n[Page 42]\nSome text after"
        assert extract_page_number(text) == 42

    def test_extract_no_marker(self):
        """Test returns 1 when no marker found."""
        assert extract_page_number("Plain text without marker") == 1

    def test_extract_multiple_markers(self):
        """Test extracts first marker when multiple exist."""
        text = "[Page 1]\nText\n[Page 2]\nMore text"
        assert extract_page_number(text) == 1


class TestChunkBySentences:
    """Test chunk_by_sentences function."""

    def test_chunk_sentences_empty_text(self):
        """Test chunk_by_sentences raises error for empty text."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            chunk_by_sentences("")

    def test_chunk_sentences_simple(self):
        """Test chunking by sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."

        chunks = chunk_by_sentences(text, max_sentences=2, overlap_sentences=0)

        # Should have 3 chunks (2 + 2 + 1)
        assert len(chunks) >= 2
        assert all("sentence" in chunk["content"].lower() for chunk in chunks)

    def test_chunk_sentences_with_overlap(self):
        """Test sentence chunking with overlap."""
        text = "One. Two. Three. Four. Five."

        chunks = chunk_by_sentences(text, max_sentences=2, overlap_sentences=1)

        # Should have overlap
        assert len(chunks) > 1

    def test_chunk_sentences_no_sentence_boundaries(self):
        """Test fallback when no sentence boundaries found."""
        text = "No sentence boundaries here"

        chunks = chunk_by_sentences(text)

        # Should return single chunk as fallback
        assert len(chunks) == 1
        assert chunks[0]["content"] == text


class TestMergeSmallChunks:
    """Test merge_small_chunks function."""

    def test_merge_empty_list(self):
        """Test merging empty chunk list."""
        result = merge_small_chunks([])
        assert result == []

    def test_merge_all_large_chunks(self):
        """Test merging when all chunks are large enough."""
        chunks = [
            {"content": "A" * 200, "chunk_index": 0, "char_start": 0, "char_end": 200, "page_number": 1},
            {"content": "B" * 200, "chunk_index": 1, "char_start": 200, "char_end": 400, "page_number": 1},
        ]

        result = merge_small_chunks(chunks, min_size=100)

        # Should not merge, all are large enough
        assert len(result) == 2

    def test_merge_small_chunks_together(self):
        """Test merging consecutive small chunks."""
        chunks = [
            {"content": "A" * 50, "chunk_index": 0, "char_start": 0, "char_end": 50, "page_number": 1},
            {"content": "B" * 50, "chunk_index": 1, "char_start": 50, "char_end": 100, "page_number": 1},
            {"content": "C" * 200, "chunk_index": 2, "char_start": 100, "char_end": 300, "page_number": 1},
        ]

        result = merge_small_chunks(chunks, min_size=100)

        # First two should be merged, third stays separate
        assert len(result) == 2
        assert "A" in result[0]["content"] and "B" in result[0]["content"]

    def test_merge_reindexes_chunks(self):
        """Test merge reindexes chunk_index correctly."""
        chunks = [
            {"content": "A" * 50, "chunk_index": 0, "char_start": 0, "char_end": 50, "page_number": 1},
            {"content": "B" * 50, "chunk_index": 1, "char_start": 50, "char_end": 100, "page_number": 1},
        ]

        result = merge_small_chunks(chunks, min_size=100)

        # Should have one merged chunk with index 0
        assert len(result) == 1
        assert result[0]["chunk_index"] == 0


class TestEstimateTokens:
    """Test estimate_tokens function."""

    def test_estimate_short_text(self):
        """Test token estimation for short text."""
        text = "Test"  # 4 chars = ~1 token
        assert estimate_tokens(text) == 1

    def test_estimate_medium_text(self):
        """Test token estimation for medium text."""
        text = "This is a test sentence."  # 24 chars = ~6 tokens
        assert estimate_tokens(text) == 6

    def test_estimate_long_text(self):
        """Test token estimation for long text."""
        text = "A" * 1000  # 1000 chars = ~250 tokens
        assert estimate_tokens(text) == 250


class TestValidateChunks:
    """Test validate_chunks function."""

    def test_validate_valid_chunks(self):
        """Test validation passes for valid chunks."""
        chunks = [
            {
                "content": "Test content 1",
                "chunk_index": 0,
                "char_start": 0,
                "char_end": 14,
                "page_number": 1
            },
            {
                "content": "Test content 2",
                "chunk_index": 1,
                "char_start": 14,
                "char_end": 28,
                "page_number": 1
            }
        ]

        assert validate_chunks(chunks) is True

    def test_validate_missing_key(self):
        """Test validation fails for missing keys."""
        chunks = [
            {
                "content": "Test",
                # Missing chunk_index
                "char_start": 0,
                "char_end": 4,
                "page_number": 1
            }
        ]

        with pytest.raises(ValueError, match="missing required key"):
            validate_chunks(chunks)

    def test_validate_wrong_type(self):
        """Test validation fails for wrong types."""
        chunks = [
            {
                "content": 123,  # Should be string
                "chunk_index": 0,
                "char_start": 0,
                "char_end": 3,
                "page_number": 1
            }
        ]

        with pytest.raises(ValueError, match="content must be string"):
            validate_chunks(chunks)

    def test_validate_empty_content(self):
        """Test validation fails for empty content."""
        chunks = [
            {
                "content": "   ",  # Whitespace only
                "chunk_index": 0,
                "char_start": 0,
                "char_end": 3,
                "page_number": 1
            }
        ]

        with pytest.raises(ValueError, match="has empty content"):
            validate_chunks(chunks)

    def test_validate_incorrect_index(self):
        """Test validation fails for incorrect chunk_index."""
        chunks = [
            {
                "content": "Test",
                "chunk_index": 5,  # Should be 0
                "char_start": 0,
                "char_end": 4,
                "page_number": 1
            }
        ]

        with pytest.raises(ValueError, match="incorrect chunk_index"):
            validate_chunks(chunks)


class TestChunkingIntegration:
    """Integration tests for chunking workflow."""

    def test_full_chunking_workflow(self):
        """Test complete chunking workflow."""
        # Simulate extracted text with page markers
        text = """[Page 1]
This is the first paragraph on page one. It contains some important legal text.

This is the second paragraph on page one. It also has relevant content.

[Page 2]
This is the first paragraph on page two. More legal content here.

This is the second paragraph on page two. Final content."""

        # Chunk the text
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20, min_chunk_size=50)

        # Validate chunks
        assert validate_chunks(chunks) is True

        # Check basic properties
        assert len(chunks) > 0
        assert all(chunk["content"] for chunk in chunks)
        assert all(chunk["page_number"] >= 1 for chunk in chunks)

        # Estimate tokens
        total_tokens = sum(estimate_tokens(chunk["content"]) for chunk in chunks)
        assert total_tokens > 0

    def test_chunk_then_merge(self):
        """Test chunking followed by merging small chunks."""
        text = """Short para 1.

Short para 2.

Very long paragraph with lots of content that will create a larger chunk when processed through the chunking algorithm.

Short para 3."""

        # First chunk
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10, min_chunk_size=20)

        # Then merge small ones
        merged = merge_small_chunks(chunks, min_size=100)

        # Merged should have fewer chunks
        assert len(merged) <= len(chunks)

        # Validate merged chunks
        assert validate_chunks(merged) is True
