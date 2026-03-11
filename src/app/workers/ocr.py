"""
OCR implementation using Tesseract.

Handles scanned PDFs and images.
"""
import logging
from pathlib import Path
from typing import Dict, Any

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    # Set to None for mocking in tests
    pytesseract = None
    Image = None
    convert_from_path = None
    logging.warning("OCR dependencies not installed. Install with: pip install pytesseract pillow pdf2image")

logger = logging.getLogger(__name__)


def perform_ocr(file_path: str) -> Dict[str, Any]:
    """
    Perform OCR on document.

    Args:
        file_path: Path to PDF or image file

    Returns:
        {
            "text": "Extracted text",
            "confidence": 85.5,  # Average confidence score (0-100)
            "page_count": 3
        }

    Raises:
        RuntimeError: If OCR dependencies not installed
        ValueError: If file type not supported
        FileNotFoundError: If file doesn't exist
    """
    if not OCR_AVAILABLE:
        raise RuntimeError(
            "OCR dependencies not installed. "
            "Install with: pip install pytesseract pillow pdf2image"
        )

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = file_path_obj.suffix.lower()

    if file_ext == '.pdf':
        return _ocr_pdf(file_path)
    elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
        return _ocr_image(file_path)
    else:
        raise ValueError(f"Unsupported file type for OCR: {file_ext}")


def _ocr_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    OCR a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        OCR result with text, confidence, page_count
    """
    logger.info(f"Starting OCR for PDF: {pdf_path}")

    try:
        # Convert PDF to images (one per page)
        # DPI 300 provides good balance between quality and processing time
        images = convert_from_path(pdf_path, dpi=300)
        logger.debug(f"Converted PDF to {len(images)} images")

        all_text = []
        confidences = []

        for i, image in enumerate(images):
            logger.debug(f"Processing page {i+1}/{len(images)}")

            # Perform OCR on each page
            # image_to_data returns detailed OCR results with confidence scores
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            # Extract text from each detected word
            # Filter out empty detections (conf = -1 or 0)
            page_text = " ".join([
                text for text, conf in zip(data['text'], data['conf'])
                if conf > 0 and text.strip()  # Skip empty/low-confidence detections
            ])

            if page_text.strip():
                # Add page marker for chunking later
                all_text.append(f"[Page {i+1}]\n{page_text}")

            # Calculate average confidence for page
            valid_confidences = [c for c in data['conf'] if c > 0]
            if valid_confidences:
                page_confidence = sum(valid_confidences) / len(valid_confidences)
                confidences.append(page_confidence)
                logger.debug(f"Page {i+1} OCR confidence: {page_confidence:.1f}%")

        # Combine all pages
        full_text = "\n\n".join(all_text)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        logger.info(f"OCR completed: {len(images)} pages, {len(full_text)} chars, {avg_confidence:.1f}% confidence")

        return {
            "text": full_text,
            "confidence": round(avg_confidence, 2),
            "page_count": len(images)
        }

    except Exception as e:
        logger.error(f"OCR failed for PDF {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"OCR processing failed: {str(e)}")


def _ocr_image(image_path: str) -> Dict[str, Any]:
    """
    OCR an image file.

    Args:
        image_path: Path to image file

    Returns:
        OCR result with text, confidence, page_count
    """
    logger.info(f"Starting OCR for image: {image_path}")

    try:
        # Open image
        image = Image.open(image_path)

        # Get detailed OCR data with confidence scores
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Extract text from detected words
        text = " ".join([
            t for t, conf in zip(data['text'], data['conf'])
            if conf > 0 and t.strip()
        ])

        # Calculate average confidence
        valid_confidences = [c for c in data['conf'] if c > 0]
        avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0

        logger.info(f"OCR completed: {len(text)} chars, {avg_confidence:.1f}% confidence")

        return {
            "text": text,
            "confidence": round(avg_confidence, 2),
            "page_count": 1
        }

    except Exception as e:
        logger.error(f"OCR failed for image {image_path}: {e}", exc_info=True)
        raise RuntimeError(f"OCR processing failed: {str(e)}")


def check_ocr_available() -> bool:
    """
    Check if OCR dependencies are available.

    Returns:
        True if pytesseract, PIL, and pdf2image are installed
    """
    return OCR_AVAILABLE


def get_tesseract_version() -> str:
    """
    Get Tesseract OCR version.

    Returns:
        Version string (e.g., "5.3.0")

    Raises:
        RuntimeError: If Tesseract not installed
    """
    if not OCR_AVAILABLE:
        raise RuntimeError("OCR dependencies not installed")

    try:
        return pytesseract.get_tesseract_version().public
    except Exception as e:
        raise RuntimeError(f"Failed to get Tesseract version: {str(e)}")
