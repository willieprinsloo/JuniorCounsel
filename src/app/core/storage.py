"""
File storage abstraction for uploaded documents.

Supports local filesystem (development) and S3 (production).
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings


class FileStorage:
    """
    File storage handler.

    In development: Saves to local filesystem (UPLOAD_FOLDER)
    In production: Can be extended to use S3/cloud storage
    """

    def __init__(self):
        """Initialize storage with upload folder from settings."""
        self.upload_folder = settings.UPLOAD_FOLDER or "./uploads"
        # Only create directory on first use, not during import
        self._ensure_upload_folder()

    def _ensure_upload_folder(self):
        """Ensure upload folder exists (called lazily)."""
        try:
            Path(self.upload_folder).mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # If default path fails, use /tmp
            self.upload_folder = "/tmp/junior_counsel_uploads"
            Path(self.upload_folder).mkdir(parents=True, exist_ok=True)

    def save_file(self, file: UploadFile, case_id: str) -> tuple[str, str]:
        """
        Save uploaded file to storage.

        Args:
            file: Uploaded file from FastAPI
            case_id: Case ID for organization

        Returns:
            Tuple of (file_path, storage_url)
            - file_path: Relative path for database storage
            - storage_url: Full path for file access
        """
        # Generate unique filename to avoid collisions
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Organize by case
        case_folder = Path(self.upload_folder) / case_id
        case_folder.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = case_folder / unique_filename
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)

        # Return relative path and full path
        relative_path = f"{case_id}/{unique_filename}"
        storage_url = str(file_path.absolute())

        return relative_path, storage_url

    def get_file_path(self, relative_path: str) -> str:
        """
        Get full file path from relative path.

        Args:
            relative_path: Relative path stored in database

        Returns:
            Full filesystem path
        """
        return str(Path(self.upload_folder) / relative_path)

    def file_exists(self, relative_path: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            relative_path: Relative path stored in database

        Returns:
            True if file exists
        """
        full_path = self.get_file_path(relative_path)
        return Path(full_path).exists()

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            relative_path: Relative path stored in database

        Returns:
            True if file was deleted
        """
        full_path = self.get_file_path(relative_path)
        try:
            Path(full_path).unlink()
            return True
        except FileNotFoundError:
            return False


def detect_needs_ocr(file: UploadFile) -> bool:
    """
    Detect if file needs OCR processing.

    Heuristics:
    - Image files (jpg, png, tiff) always need OCR
    - PDF files: Check if image-based (Phase 3 - use pypdf to detect)
    - For now: Conservative approach - assume PDFs might need OCR

    Args:
        file: Uploaded file

    Returns:
        True if OCR is likely needed
    """
    filename = file.filename.lower()

    # Image files always need OCR
    if filename.endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp')):
        return True

    # PDF files: Assume might need OCR (refine in Phase 3)
    if filename.endswith('.pdf'):
        # TODO: In Phase 3, use pypdf to check if PDF has text layer
        # For now, conservative: assume OCR needed
        return True

    # Word docs, txt files don't need OCR
    return False


# Global storage instance
storage = FileStorage()
