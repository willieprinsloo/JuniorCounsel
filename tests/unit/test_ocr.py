"""
Unit tests for OCR module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path


class TestPerformOCR:
    """Test perform_ocr function."""

    @patch('app.workers.ocr.OCR_AVAILABLE', False)
    def test_ocr_not_available(self):
        """Test perform_ocr raises error when dependencies not installed."""
        from app.workers.ocr import perform_ocr

        with pytest.raises(RuntimeError, match="OCR dependencies not installed"):
            perform_ocr("test.pdf")

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    def test_file_not_found(self):
        """Test perform_ocr raises error for non-existent file."""
        from app.workers.ocr import perform_ocr

        with pytest.raises(FileNotFoundError, match="File not found"):
            perform_ocr("/nonexistent/file.pdf")

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    @patch('app.workers.ocr.Path')
    def test_unsupported_file_type(self, mock_path):
        """Test perform_ocr raises error for unsupported file type."""
        from app.workers.ocr import perform_ocr

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.txt'
        mock_path.return_value = mock_path_obj

        with pytest.raises(ValueError, match="Unsupported file type for OCR: .txt"):
            perform_ocr("test.txt")

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    @patch('app.workers.ocr._ocr_pdf')
    @patch('app.workers.ocr.Path')
    def test_routes_to_pdf_ocr(self, mock_path, mock_ocr_pdf):
        """Test perform_ocr routes PDF files to _ocr_pdf."""
        from app.workers.ocr import perform_ocr

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.pdf'
        mock_path.return_value = mock_path_obj

        mock_ocr_pdf.return_value = {"text": "Test", "confidence": 90.0, "page_count": 1}

        result = perform_ocr("test.pdf")

        assert result["text"] == "Test"
        mock_ocr_pdf.assert_called_once_with("test.pdf")

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    @patch('app.workers.ocr._ocr_image')
    @patch('app.workers.ocr.Path')
    def test_routes_to_image_ocr(self, mock_path, mock_ocr_image):
        """Test perform_ocr routes image files to _ocr_image."""
        from app.workers.ocr import perform_ocr

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.jpg'
        mock_path.return_value = mock_path_obj

        mock_ocr_image.return_value = {"text": "Image text", "confidence": 85.0, "page_count": 1}

        result = perform_ocr("test.jpg")

        assert result["text"] == "Image text"
        mock_ocr_image.assert_called_once_with("test.jpg")

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    @patch('app.workers.ocr._ocr_image')
    @patch('app.workers.ocr.Path')
    @pytest.mark.parametrize("ext", ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'])
    def test_supports_all_image_formats(self, mock_path, mock_ocr_image, ext):
        """Test perform_ocr supports all common image formats."""
        from app.workers.ocr import perform_ocr

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = ext
        mock_path.return_value = mock_path_obj

        mock_ocr_image.return_value = {"text": "Test", "confidence": 90.0, "page_count": 1}

        result = perform_ocr(f"test{ext}")

        assert result["text"] == "Test"
        mock_ocr_image.assert_called_once()


class TestOCRPDF:
    """Test _ocr_pdf function."""

    def test_ocr_single_page_pdf(self):
        """Test OCR on single-page PDF."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.convert_from_path') as mock_convert:
                with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                    from app.workers.ocr import _ocr_pdf

                    # Mock PDF conversion to images
                    mock_image = Mock()
                    mock_convert.return_value = [mock_image]

                    # Mock OCR data
                    mock_pytesseract.image_to_data.return_value = {
                        'text': ['This', 'is', 'a', 'test'],
                        'conf': [95, 90, 88, 92]
                    }
                    mock_pytesseract.Output.DICT = 'dict'

                    result = _ocr_pdf("test.pdf")

                    assert result["text"] == "[Page 1]\nThis is a test"
                    assert result["confidence"] == pytest.approx(91.25, rel=0.1)
                    assert result["page_count"] == 1
                    mock_convert.assert_called_once_with("test.pdf", dpi=300)

    def test_ocr_multi_page_pdf(self):
        """Test OCR on multi-page PDF."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.convert_from_path') as mock_convert:
                with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                    from app.workers.ocr import _ocr_pdf

                    # Mock PDF conversion to 3 images
                    mock_convert.return_value = [Mock(), Mock(), Mock()]

                    # Mock OCR data for each page
                    mock_pytesseract.image_to_data.return_value = {
                        'text': ['Page', 'text'],
                        'conf': [90, 85]
                    }
                    mock_pytesseract.Output.DICT = 'dict'

                    result = _ocr_pdf("test.pdf")

                    assert result["page_count"] == 3
                    assert "[Page 1]" in result["text"]
                    assert "[Page 2]" in result["text"]
                    assert "[Page 3]" in result["text"]
                    assert mock_pytesseract.image_to_data.call_count == 3

    def test_ocr_pdf_filters_low_confidence(self):
        """Test OCR filters out low-confidence and empty detections."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.convert_from_path') as mock_convert:
                with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                    from app.workers.ocr import _ocr_pdf

                    mock_convert.return_value = [Mock()]

                    # Mock OCR data with some low-confidence and empty detections
                    mock_pytesseract.image_to_data.return_value = {
                        'text': ['Good', '', 'text', 'bad'],
                        'conf': [95, 0, 90, -1]
                    }
                    mock_pytesseract.Output.DICT = 'dict'

                    result = _ocr_pdf("test.pdf")

                    # Should only include 'Good' and 'text', skip empty and low-confidence
                    assert result["text"] == "[Page 1]\nGood text"
                    assert result["confidence"] == pytest.approx(92.5, rel=0.1)

    def test_ocr_pdf_handles_conversion_error(self):
        """Test _ocr_pdf handles PDF conversion errors."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.convert_from_path') as mock_convert:
                from app.workers.ocr import _ocr_pdf

                mock_convert.side_effect = Exception("PDF conversion failed")

                with pytest.raises(RuntimeError, match="OCR processing failed"):
                    _ocr_pdf("test.pdf")


class TestOCRImage:
    """Test _ocr_image function."""

    def test_ocr_image_success(self):
        """Test successful image OCR."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.Image') as mock_image_class:
                with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                    from app.workers.ocr import _ocr_image

                    # Mock image opening
                    mock_image = Mock()
                    mock_image_class.open.return_value = mock_image

                    # Mock OCR data
                    mock_pytesseract.image_to_data.return_value = {
                        'text': ['Sample', 'image', 'text'],
                        'conf': [88, 92, 90]
                    }
                    mock_pytesseract.Output.DICT = 'dict'

                    result = _ocr_image("test.jpg")

                    assert result["text"] == "Sample image text"
                    assert result["confidence"] == pytest.approx(90.0, rel=0.1)
                    assert result["page_count"] == 1
                    mock_image_class.open.assert_called_once_with("test.jpg")

    def test_ocr_image_filters_empty_text(self):
        """Test image OCR filters empty text."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.Image') as mock_image_class:
                with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                    from app.workers.ocr import _ocr_image

                    mock_image_class.open.return_value = Mock()

                    # Mock OCR data with empty strings
                    mock_pytesseract.image_to_data.return_value = {
                        'text': ['Hello', '', 'world', '   '],
                        'conf': [95, 0, 90, 85]
                    }
                    mock_pytesseract.Output.DICT = 'dict'

                    result = _ocr_image("test.jpg")

                    # Should skip empty and whitespace-only strings
                    assert result["text"] == "Hello world"

    def test_ocr_image_handles_open_error(self):
        """Test _ocr_image handles image open errors."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.Image') as mock_image_class:
                from app.workers.ocr import _ocr_image

                mock_image_class.open.side_effect = Exception("Cannot open image")

                with pytest.raises(RuntimeError, match="OCR processing failed"):
                    _ocr_image("test.jpg")


class TestOCRUtilities:
    """Test OCR utility functions."""

    @patch('app.workers.ocr.OCR_AVAILABLE', True)
    def test_check_ocr_available_true(self):
        """Test check_ocr_available returns True when installed."""
        from app.workers.ocr import check_ocr_available

        assert check_ocr_available() is True

    @patch('app.workers.ocr.OCR_AVAILABLE', False)
    def test_check_ocr_available_false(self):
        """Test check_ocr_available returns False when not installed."""
        from app.workers.ocr import check_ocr_available

        assert check_ocr_available() is False

    @patch('app.workers.ocr.OCR_AVAILABLE', False)
    def test_get_tesseract_version_not_available(self):
        """Test get_tesseract_version raises error when not installed."""
        from app.workers.ocr import get_tesseract_version

        with pytest.raises(RuntimeError, match="OCR dependencies not installed"):
            get_tesseract_version()

    def test_get_tesseract_version_success(self):
        """Test get_tesseract_version returns version string."""
        with patch('app.workers.ocr.OCR_AVAILABLE', True):
            with patch('app.workers.ocr.pytesseract') as mock_pytesseract:
                from app.workers.ocr import get_tesseract_version

                mock_version = Mock()
                mock_version.public = "5.3.0"
                mock_pytesseract.get_tesseract_version.return_value = mock_version

                version = get_tesseract_version()

                assert version == "5.3.0"
