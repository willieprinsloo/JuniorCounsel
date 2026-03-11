"""
Unit tests for text extraction module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestExtractTextFromPDF:
    """Test extract_text_from_pdf function."""

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', False)
    def test_pypdf_not_available(self):
        """Test extract_text_from_pdf raises error when pypdf not installed."""
        from app.workers.text_extraction import extract_text_from_pdf

        with pytest.raises(RuntimeError, match="pypdf not installed"):
            extract_text_from_pdf("test.pdf")

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', True)
    def test_file_not_found(self):
        """Test extract_text_from_pdf raises error for non-existent file."""
        from app.workers.text_extraction import extract_text_from_pdf

        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text_from_pdf("/nonexistent/file.pdf")

    def test_extract_single_page_pdf(self):
        """Test extracting text from single-page PDF."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_pdf

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mock PDF reader
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "This is test content from the PDF."

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page]
                    mock_reader_class.return_value = mock_reader

                    result = extract_text_from_pdf("test.pdf")

                    assert result == "[Page 1]\nThis is test content from the PDF."
                    mock_reader_class.assert_called_once_with("test.pdf")

    def test_extract_multi_page_pdf(self):
        """Test extracting text from multi-page PDF."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_pdf

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mock 3 pages
                    mock_page1 = Mock()
                    mock_page1.extract_text.return_value = "Page 1 content"
                    mock_page2 = Mock()
                    mock_page2.extract_text.return_value = "Page 2 content"
                    mock_page3 = Mock()
                    mock_page3.extract_text.return_value = "Page 3 content"

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page1, mock_page2, mock_page3]
                    mock_reader_class.return_value = mock_reader

                    result = extract_text_from_pdf("test.pdf")

                    assert "[Page 1]\nPage 1 content" in result
                    assert "[Page 2]\nPage 2 content" in result
                    assert "[Page 3]\nPage 3 content" in result

    def test_extract_pdf_with_empty_pages(self):
        """Test extracting text from PDF with some empty pages."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_pdf

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Page 1 has text, Page 2 is empty, Page 3 has text
                    mock_page1 = Mock()
                    mock_page1.extract_text.return_value = "Page 1 content"
                    mock_page2 = Mock()
                    mock_page2.extract_text.return_value = "   "  # Whitespace only
                    mock_page3 = Mock()
                    mock_page3.extract_text.return_value = "Page 3 content"

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page1, mock_page2, mock_page3]
                    mock_reader_class.return_value = mock_reader

                    result = extract_text_from_pdf("test.pdf")

                    # Should only include pages with actual content
                    assert "[Page 1]\nPage 1 content" in result
                    assert "[Page 3]\nPage 3 content" in result
                    assert "[Page 2]" not in result

    def test_extract_pdf_handles_page_error(self):
        """Test extraction continues when individual page fails."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_pdf

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Page 1 succeeds, Page 2 fails, Page 3 succeeds
                    mock_page1 = Mock()
                    mock_page1.extract_text.return_value = "Page 1 content"
                    mock_page2 = Mock()
                    mock_page2.extract_text.side_effect = Exception("Page extraction failed")
                    mock_page3 = Mock()
                    mock_page3.extract_text.return_value = "Page 3 content"

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page1, mock_page2, mock_page3]
                    mock_reader_class.return_value = mock_reader

                    result = extract_text_from_pdf("test.pdf")

                    # Should extract pages 1 and 3, skip page 2
                    assert "[Page 1]\nPage 1 content" in result
                    assert "[Page 3]\nPage 3 content" in result


class TestExtractTextFromDOCX:
    """Test extract_text_from_docx function."""

    @patch('app.workers.text_extraction.DOCX_AVAILABLE', False)
    def test_docx_not_available(self):
        """Test extract_text_from_docx raises error when python-docx not installed."""
        from app.workers.text_extraction import extract_text_from_docx

        with pytest.raises(RuntimeError, match="python-docx not installed"):
            extract_text_from_docx("test.docx")

    @patch('app.workers.text_extraction.DOCX_AVAILABLE', True)
    def test_file_not_found(self):
        """Test extract_text_from_docx raises error for non-existent file."""
        from app.workers.text_extraction import extract_text_from_docx

        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text_from_docx("/nonexistent/file.docx")

    def test_extract_docx_success(self):
        """Test successful DOCX text extraction."""
        with patch('app.workers.text_extraction.DOCX_AVAILABLE', True):
            with patch('app.workers.text_extraction.docx') as mock_docx_module:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_docx

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mock document with paragraphs
                    mock_para1 = Mock()
                    mock_para1.text = "First paragraph"
                    mock_para2 = Mock()
                    mock_para2.text = "Second paragraph"
                    mock_para3 = Mock()
                    mock_para3.text = "Third paragraph"

                    mock_doc = Mock()
                    mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
                    mock_docx_module.Document.return_value = mock_doc

                    result = extract_text_from_docx("test.docx")

                    assert result == "First paragraph\n\nSecond paragraph\n\nThird paragraph"
                    mock_docx_module.Document.assert_called_once_with("test.docx")

    def test_extract_docx_filters_empty_paragraphs(self):
        """Test DOCX extraction filters empty paragraphs."""
        with patch('app.workers.text_extraction.DOCX_AVAILABLE', True):
            with patch('app.workers.text_extraction.docx') as mock_docx_module:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import extract_text_from_docx

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mix of content and empty paragraphs
                    mock_para1 = Mock()
                    mock_para1.text = "First paragraph"
                    mock_para2 = Mock()
                    mock_para2.text = "   "  # Whitespace only
                    mock_para3 = Mock()
                    mock_para3.text = "Third paragraph"

                    mock_doc = Mock()
                    mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
                    mock_docx_module.Document.return_value = mock_doc

                    result = extract_text_from_docx("test.docx")

                    # Should skip empty paragraph
                    assert result == "First paragraph\n\nThird paragraph"


class TestExtractText:
    """Test extract_text routing function."""

    @patch('app.workers.text_extraction.Path')
    def test_file_not_found(self, mock_path):
        """Test extract_text raises error for non-existent file."""
        from app.workers.text_extraction import extract_text

        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = False
        mock_path.return_value = mock_path_obj

        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text("nonexistent.pdf")

    @patch('app.workers.ocr.perform_ocr')
    @patch('app.workers.text_extraction.Path')
    def test_routes_to_ocr_when_needed(self, mock_path, mock_ocr):
        """Test extract_text routes to OCR when needs_ocr=True."""
        from app.workers.text_extraction import extract_text

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.pdf'
        mock_path.return_value = mock_path_obj

        mock_ocr.return_value = {"text": "OCR extracted text"}

        result = extract_text("test.pdf", needs_ocr=True)

        assert result == "OCR extracted text"
        mock_ocr.assert_called_once_with("test.pdf")

    @patch('app.workers.text_extraction.extract_text_from_pdf')
    @patch('app.workers.text_extraction.Path')
    def test_routes_to_pdf_extraction(self, mock_path, mock_pdf_extract):
        """Test extract_text routes PDF files to extract_text_from_pdf."""
        from app.workers.text_extraction import extract_text

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.pdf'
        mock_path.return_value = mock_path_obj

        mock_pdf_extract.return_value = "PDF text content"

        result = extract_text("test.pdf", needs_ocr=False)

        assert result == "PDF text content"
        mock_pdf_extract.assert_called_once_with("test.pdf")

    @patch('app.workers.text_extraction.extract_text_from_docx')
    @patch('app.workers.text_extraction.Path')
    def test_routes_to_docx_extraction(self, mock_path, mock_docx_extract):
        """Test extract_text routes DOCX files to extract_text_from_docx."""
        from app.workers.text_extraction import extract_text

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.docx'
        mock_path.return_value = mock_path_obj

        mock_docx_extract.return_value = "DOCX text content"

        result = extract_text("test.docx")

        assert result == "DOCX text content"
        mock_docx_extract.assert_called_once_with("test.docx")

    @patch('app.workers.text_extraction.Path')
    def test_unsupported_file_type(self, mock_path):
        """Test extract_text raises error for unsupported file types."""
        from app.workers.text_extraction import extract_text

        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.txt'
        mock_path.return_value = mock_path_obj

        with pytest.raises(ValueError, match="Unsupported file type: .txt"):
            extract_text("test.txt")


class TestHasTextLayer:
    """Test has_text_layer function."""

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', False)
    def test_pypdf_not_available(self):
        """Test has_text_layer raises error when pypdf not installed."""
        from app.workers.text_extraction import has_text_layer

        with pytest.raises(RuntimeError, match="pypdf not installed"):
            has_text_layer("test.pdf")

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', True)
    def test_file_not_found(self):
        """Test has_text_layer raises error for non-existent file."""
        from app.workers.text_extraction import has_text_layer

        with pytest.raises(FileNotFoundError, match="File not found"):
            has_text_layer("/nonexistent/file.pdf")

    def test_pdf_with_text_layer(self):
        """Test has_text_layer returns True for text-based PDF."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import has_text_layer

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mock page with substantial text (> 50 chars)
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "This is a text-based PDF with more than 50 characters of content."

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page]
                    mock_reader_class.return_value = mock_reader

                    result = has_text_layer("test.pdf")

                    assert result is True

    def test_pdf_without_text_layer(self):
        """Test has_text_layer returns False for scanned PDF."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import has_text_layer

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path.return_value = mock_path_obj

                    # Mock page with minimal text (< 50 chars)
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "   "  # Whitespace

                    mock_reader = Mock()
                    mock_reader.pages = [mock_page]
                    mock_reader_class.return_value = mock_reader

                    result = has_text_layer("test.pdf")

                    assert result is False


class TestGetPageCount:
    """Test get_page_count function."""

    @patch('app.workers.text_extraction.Path')
    def test_file_not_found(self, mock_path):
        """Test get_page_count raises error for non-existent file."""
        from app.workers.text_extraction import get_page_count

        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = False
        mock_path.return_value = mock_path_obj

        with pytest.raises(FileNotFoundError, match="File not found"):
            get_page_count("nonexistent.pdf")

    def test_get_page_count_pdf(self):
        """Test get_page_count for PDF."""
        with patch('app.workers.text_extraction.PYPDF_AVAILABLE', True):
            with patch('app.workers.text_extraction.PdfReader') as mock_reader_class:
                with patch('app.workers.text_extraction.Path') as mock_path:
                    from app.workers.text_extraction import get_page_count

                    # Mock file exists
                    mock_path_obj = MagicMock()
                    mock_path_obj.exists.return_value = True
                    mock_path_obj.suffix = '.pdf'
                    mock_path.return_value = mock_path_obj

                    # Mock 5-page PDF
                    mock_reader = Mock()
                    mock_reader.pages = [Mock()] * 5
                    mock_reader_class.return_value = mock_reader

                    result = get_page_count("test.pdf")

                    assert result == 5

    @patch('app.workers.text_extraction.Path')
    def test_get_page_count_docx(self, mock_path):
        """Test get_page_count for DOCX (always returns 1)."""
        from app.workers.text_extraction import get_page_count

        # Mock file exists
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.docx'
        mock_path.return_value = mock_path_obj

        result = get_page_count("test.docx")

        assert result == 1

    @patch('app.workers.text_extraction.Path')
    def test_get_page_count_unsupported(self, mock_path):
        """Test get_page_count raises error for unsupported file type."""
        from app.workers.text_extraction import get_page_count

        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = '.txt'
        mock_path.return_value = mock_path_obj

        with pytest.raises(ValueError, match="Unsupported file type"):
            get_page_count("test.txt")


class TestCheckTextExtractionAvailable:
    """Test check_text_extraction_available function."""

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', True)
    @patch('app.workers.text_extraction.DOCX_AVAILABLE', True)
    def test_all_available(self):
        """Test check returns True for all when installed."""
        from app.workers.text_extraction import check_text_extraction_available

        result = check_text_extraction_available()

        assert result["pypdf"] is True
        assert result["docx"] is True

    @patch('app.workers.text_extraction.PYPDF_AVAILABLE', False)
    @patch('app.workers.text_extraction.DOCX_AVAILABLE', False)
    def test_none_available(self):
        """Test check returns False for all when not installed."""
        from app.workers.text_extraction import check_text_extraction_available

        result = check_text_extraction_available()

        assert result["pypdf"] is False
        assert result["docx"] is False
