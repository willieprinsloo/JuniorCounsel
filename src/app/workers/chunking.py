"""
Text chunking for embedding generation.

Splits documents into semantic chunks suitable for vector search.
"""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    min_chunk_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Split text into chunks for embedding.

    Strategy:
    1. Split by paragraphs first (double newlines)
    2. Combine small paragraphs to meet min_chunk_size
    3. Split large paragraphs if they exceed chunk_size
    4. Add overlap between chunks for context continuity
    5. Extract page numbers from [Page N] markers

    Args:
        text: Document text to chunk
        chunk_size: Target chunk size in characters (~512 tokens = ~2048 chars)
        chunk_overlap: Overlap between chunks in characters (for context continuity)
        min_chunk_size: Minimum chunk size in characters (skip very small chunks)

    Returns:
        List of chunk dicts with metadata:
        [
            {
                "content": "chunk text",
                "chunk_index": 0,
                "char_start": 0,
                "char_end": 500,
                "page_number": 1
            },
            ...
        ]

    Raises:
        ValueError: If text is empty or invalid parameters
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if chunk_size < min_chunk_size:
        raise ValueError(f"chunk_size ({chunk_size}) must be >= min_chunk_size ({min_chunk_size})")

    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap ({chunk_overlap}) must be < chunk_size ({chunk_size})")

    logger.debug(f"Chunking text: {len(text)} chars, chunk_size={chunk_size}, overlap={chunk_overlap}")

    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = ""
    current_char_start = 0
    current_char_position = 0

    for para in paragraphs:
        # Calculate target size (4 chars per token approximation)
        target_char_size = chunk_size * 4

        # If adding this paragraph would exceed chunk_size, save current chunk
        if current_chunk and len(current_chunk) + len(para) + 2 > target_char_size:
            # Only save if meets minimum size
            if len(current_chunk) >= min_chunk_size:
                # Extract page number from chunk
                page_num = extract_page_number(current_chunk)

                chunks.append({
                    "content": current_chunk,
                    "chunk_index": len(chunks),
                    "char_start": current_char_start,
                    "char_end": current_char_start + len(current_chunk),
                    "page_number": page_num
                })

                # Start new chunk with overlap
                overlap_text = ""
                if chunk_overlap > 0:
                    # Take last chunk_overlap*4 characters as overlap
                    overlap_size = chunk_overlap * 4
                    overlap_text = current_chunk[-overlap_size:] if len(current_chunk) > overlap_size else current_chunk

                # Update position tracking
                current_char_start += len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text
                if overlap_text:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # Chunk too small, just add to it
                current_chunk += "\n\n" + para
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
                current_char_start = current_char_position

        current_char_position += len(para) + 2  # +2 for \n\n

    # Add final chunk if it meets minimum size
    if current_chunk and len(current_chunk) >= min_chunk_size:
        page_num = extract_page_number(current_chunk)

        chunks.append({
            "content": current_chunk,
            "chunk_index": len(chunks),
            "char_start": current_char_start,
            "char_end": current_char_start + len(current_chunk),
            "page_number": page_num
        })

    logger.info(f"Created {len(chunks)} chunks from {len(text)} chars")

    return chunks


def extract_page_number(chunk_text: str) -> int:
    """
    Extract page number from chunk text.

    Looks for [Page N] markers inserted during text extraction.

    Args:
        chunk_text: Chunk content

    Returns:
        Page number (or 1 if no marker found)
    """
    # Look for [Page N] marker
    match = re.search(r'\[Page (\d+)\]', chunk_text)
    if match:
        return int(match.group(1))

    # Default to page 1
    return 1


def chunk_by_sentences(
    text: str,
    max_sentences: int = 5,
    overlap_sentences: int = 1
) -> List[Dict[str, Any]]:
    """
    Split text into chunks by sentences.

    Alternative chunking strategy for more semantic coherence.

    Args:
        text: Text to chunk
        max_sentences: Maximum sentences per chunk
        overlap_sentences: Number of overlapping sentences between chunks

    Returns:
        List of chunk dicts
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    logger.debug(f"Chunking by sentences: max={max_sentences}, overlap={overlap_sentences}")

    # Split into sentences (simple approach - can be improved)
    # Handles ., !, ? followed by space or newline
    sentence_pattern = r'([^.!?]+[.!?](?:\s|$))'
    sentences = re.findall(sentence_pattern, text)

    if not sentences:
        # Fallback if no sentence boundaries found
        return [{
            "content": text,
            "chunk_index": 0,
            "char_start": 0,
            "char_end": len(text),
            "page_number": extract_page_number(text)
        }]

    chunks = []
    i = 0

    while i < len(sentences):
        # Take max_sentences
        chunk_sentences = sentences[i:i+max_sentences]
        chunk_text = "".join(chunk_sentences).strip()

        if chunk_text:
            chunks.append({
                "content": chunk_text,
                "chunk_index": len(chunks),
                "char_start": 0,  # Simplified - not tracking char positions
                "char_end": len(chunk_text),
                "page_number": extract_page_number(chunk_text)
            })

        # Move forward by (max_sentences - overlap_sentences)
        step = max(1, max_sentences - overlap_sentences)
        i += step

    logger.info(f"Created {len(chunks)} sentence-based chunks")

    return chunks


def merge_small_chunks(
    chunks: List[Dict[str, Any]],
    min_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Merge consecutive chunks that are smaller than min_size.

    Args:
        chunks: List of chunk dicts
        min_size: Minimum chunk size in characters

    Returns:
        List of merged chunks
    """
    if not chunks:
        return []

    merged = []
    current_merge = None

    for chunk in chunks:
        content = chunk["content"]

        if len(content) < min_size:
            # Too small, merge with current or start new merge
            if current_merge is None:
                current_merge = chunk.copy()
            else:
                # Merge with previous
                current_merge["content"] += "\n\n" + content
                current_merge["char_end"] = chunk["char_end"]
        else:
            # Large enough, save current merge and this chunk
            if current_merge is not None:
                # Check if merged chunk is now large enough
                if len(current_merge["content"]) >= min_size:
                    merged.append(current_merge)
                else:
                    # Still too small, combine with current chunk
                    chunk["content"] = current_merge["content"] + "\n\n" + chunk["content"]
                    chunk["char_start"] = current_merge["char_start"]

                current_merge = None

            merged.append(chunk)

    # Add final merge if exists
    if current_merge is not None:
        merged.append(current_merge)

    # Reindex chunks
    for i, chunk in enumerate(merged):
        chunk["chunk_index"] = i

    logger.info(f"Merged {len(chunks)} chunks into {len(merged)} chunks")

    return merged


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses simple heuristic: ~4 characters per token.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def validate_chunks(chunks: List[Dict[str, Any]]) -> bool:
    """
    Validate chunk structure.

    Args:
        chunks: List of chunk dicts

    Returns:
        True if all chunks are valid

    Raises:
        ValueError: If chunks are invalid
    """
    required_keys = ["content", "chunk_index", "char_start", "char_end", "page_number"]

    for i, chunk in enumerate(chunks):
        # Check required keys
        for key in required_keys:
            if key not in chunk:
                raise ValueError(f"Chunk {i} missing required key: {key}")

        # Check types
        if not isinstance(chunk["content"], str):
            raise ValueError(f"Chunk {i} content must be string")

        if not isinstance(chunk["chunk_index"], int):
            raise ValueError(f"Chunk {i} chunk_index must be int")

        # Check content not empty
        if not chunk["content"].strip():
            raise ValueError(f"Chunk {i} has empty content")

        # Check chunk_index matches position
        if chunk["chunk_index"] != i:
            raise ValueError(f"Chunk {i} has incorrect chunk_index: {chunk['chunk_index']}")

    return True
