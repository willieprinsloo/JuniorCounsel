"""
Text extraction from PDFs and documents.

Handles text-based PDFs (non-scanned) and DOCX files.
"""
import logging
from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    PdfReader = None
    logging.warning("pypdf not installed. Install with: pip install pypdf")

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    docx = None
    logging.warning("python-docx not installed. Install with: pip install python-docx")

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using pypdf.

    Works for text-based PDFs. For scanned PDFs, use OCR instead.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text with page markers

    Raises:
        RuntimeError: If pypdf not installed
        FileNotFoundError: If file doesn't exist
    """
    if not PYPDF_AVAILABLE:
        raise RuntimeError(
            "pypdf not installed. "
            "Install with: pip install pypdf"
        )

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    logger.info(f"Extracting text from PDF: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        logger.debug(f"PDF has {total_pages} pages")

        text_parts = []
        empty_pages = 0

        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()

                if page_text.strip():
                    # Add page marker for chunking later
                    text_parts.append(f"[Page {i+1}]\n{page_text}")
                else:
                    empty_pages += 1
                    logger.debug(f"Page {i+1} has no extractable text")

            except Exception as e:
                logger.warning(f"Failed to extract text from page {i+1}: {e}")
                empty_pages += 1

        if empty_pages == total_pages:
            logger.warning(f"PDF {pdf_path} has no extractable text - may need OCR")

        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {total_pages - empty_pages}/{total_pages} pages")

        return full_text

    except Exception as e:
        logger.error(f"Text extraction failed for PDF {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"Text extraction failed: {str(e)}")


def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract text from DOCX file.

    Args:
        docx_path: Path to DOCX file

    Returns:
        Extracted text

    Raises:
        RuntimeError: If python-docx not installed
        FileNotFoundError: If file doesn't exist
    """
    if not DOCX_AVAILABLE:
        raise RuntimeError(
            "python-docx not installed. "
            "Install with: pip install python-docx"
        )

    docx_path_obj = Path(docx_path)
    if not docx_path_obj.exists():
        raise FileNotFoundError(f"File not found: {docx_path}")

    logger.info(f"Extracting text from DOCX: {docx_path}")

    try:
        doc = docx.Document(docx_path)

        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {len(text_parts)} paragraphs")

        return full_text

    except Exception as e:
        logger.error(f"Text extraction failed for DOCX {docx_path}: {e}", exc_info=True)
        raise RuntimeError(f"Text extraction failed: {str(e)}")


def extract_text(file_path: str, needs_ocr: bool = False) -> str:
    """
    Extract text from document.

    Routes to appropriate extraction method based on file type.

    Args:
        file_path: Path to document
        needs_ocr: Whether OCR is needed (from document metadata)

    Returns:
        Extracted text

    Raises:
        ValueError: If file type not supported
        RuntimeError: If extraction fails
        FileNotFoundError: If file doesn't exist
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = file_path_obj.suffix.lower()

    # If OCR is needed, delegate to OCR module
    if needs_ocr:
        from app.workers.ocr import perform_ocr
        logger.info(f"Using OCR for {file_path}")
        result = perform_ocr(file_path)
        return result["text"]

    # Route based on file type
    if file_ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_ext in ['.docx', '.doc']:
        # .doc files require python-docx (or alternative)
        # For now, only .docx is fully supported
        if file_ext == '.doc':
            logger.warning(f".doc files may not be fully supported, attempting as .docx: {file_path}")
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


def has_text_layer(pdf_path: str) -> bool:
    """
    Check if PDF has a text layer (not scanned).

    Args:
        pdf_path: Path to PDF

    Returns:
        True if PDF has extractable text

    Raises:
        RuntimeError: If pypdf not installed
        FileNotFoundError: If file doesn't exist
    """
    if not PYPDF_AVAILABLE:
        raise RuntimeError(
            "pypdf not installed. "
            "Install with: pip install pypdf"
        )

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)

        # Check first page for text
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text()
            # If we get substantial text, it's not scanned
            has_text = len(text.strip()) > 50
            logger.debug(f"PDF {pdf_path} has_text_layer: {has_text} (first page: {len(text)} chars)")
            return has_text

        logger.warning(f"PDF {pdf_path} has no pages")
        return False

    except Exception as e:
        logger.error(f"Failed to check text layer for {pdf_path}: {e}")
        # Assume needs OCR if we can't determine
        return False


def get_page_count(file_path: str) -> int:
    """
    Get page count for document.

    Args:
        file_path: Path to document

    Returns:
        Number of pages (1 for DOCX, actual count for PDF)

    Raises:
        ValueError: If file type not supported
        FileNotFoundError: If file doesn't exist
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = file_path_obj.suffix.lower()

    if file_ext == '.pdf':
        if not PYPDF_AVAILABLE:
            raise RuntimeError("pypdf not installed")

        try:
            reader = PdfReader(file_path)
            return len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to get page count for {file_path}: {e}")
            return 1  # Default to 1 if we can't determine

    elif file_ext in ['.docx', '.doc']:
        # DOCX doesn't have clear page concept, return 1
        return 1

    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


def check_text_extraction_available() -> dict:
    """
    Check which text extraction dependencies are available.

    Returns:
        {
            "pypdf": bool,
            "docx": bool
        }
    """
    return {
        "pypdf": PYPDF_AVAILABLE,
        "docx": DOCX_AVAILABLE
    }
