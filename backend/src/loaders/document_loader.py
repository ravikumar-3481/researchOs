from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO

from langchain_core.documents import Document
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.utils.logger import logger

_log = logger.bind(service="document_loader")


class PDFReadError(Exception):
    """Raised when reading or parsing a PDF document fails."""


class PDFPage(BaseModel):
    """Structured representation of a single extracted PDF page."""

    page_number: int = Field(description="1-based index of the page in the document")
    text: str = Field(default="", description="Extracted textual content of the page")
    char_count: int = Field(default=0, description="Number of characters in page text")


class PDFDocument(BaseModel):
    """Structured representation of an entire parsed PDF document."""

    source: str = Field(description="Source identifier (file path, filename, or stream label)")
    total_pages: int = Field(description="Total number of pages in the PDF")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Cleaned document metadata dictionary",
    )
    pages: list[PDFPage] = Field(
        default_factory=list,
        description="List of individual page contents and page numbers",
    )
    text: str = Field(
        default="",
        description="Full concatenated text across all pages",
    )


def _clean_pdf_metadata(raw_metadata: Any | None) -> dict[str, Any]:
    """Normalize raw PyPDF metadata dictionary into clean key-value pairs."""
    if not raw_metadata:
        return {}

    cleaned: dict[str, Any] = {}
    for key, value in raw_metadata.items():
        if value is not None:
            # PyPDF metadata keys usually start with a slash (e.g., '/Title' -> 'Title')
            clean_key = str(key).lstrip("/").strip()
            cleaned[clean_key] = str(value).strip()
    return cleaned


def _parse_pdf_stream(
    stream: BinaryIO,
    source_name: str,
    password: str | None = None,
    page_separator: str = "\n\n",
) -> PDFDocument:
    """Parse an open binary PDF stream and return structured PDFDocument."""
    try:
        reader = PdfReader(stream)
    except PdfReadError as exc:
        raise PDFReadError(f"Corrupt or invalid PDF data from {source_name}: {exc}") from exc
    except Exception as exc:
        raise PDFReadError(f"Failed to initialize PDF reader for {source_name}: {exc}") from exc

    # Handle password-protected / encrypted PDFs
    if reader.is_encrypted:
        _log.info(f"PDF '{source_name}' is encrypted, attempting decryption")
        if password is None:
            raise PDFReadError(
                f"PDF at '{source_name}' is password-protected, but no password was provided."
            )
        decrypt_result = reader.decrypt(password)
        if decrypt_result == 0:
            raise PDFReadError(f"Incorrect password provided for encrypted PDF '{source_name}'.")

    # Extract document metadata
    raw_metadata = getattr(reader, "metadata", None)
    cleaned_metadata = _clean_pdf_metadata(raw_metadata)

    total_pages = len(reader.pages)
    pages_data: list[PDFPage] = []
    page_texts: list[str] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except (PdfReadError, ValueError, KeyError, TypeError, OSError, UnicodeDecodeError) as exc:
            _log.warning(f"Failed to extract text from page {idx} in '{source_name}': {exc}")
            page_text = ""

        page_item = PDFPage(
            page_number=idx,
            text=page_text,
            char_count=len(page_text),
        )
        pages_data.append(page_item)
        if page_text.strip():
            page_texts.append(page_text)

    full_text = page_separator.join(page_texts)

    _log.info(
        f"Successfully read PDF '{source_name}': {total_pages} pages, {len(full_text)} characters"
    )

    return PDFDocument(
        source=source_name,
        total_pages=total_pages,
        metadata=cleaned_metadata,
        pages=pages_data,
        text=full_text,
    )


def read_pdf(
    source: str | Path | bytes | BinaryIO,
    password: str | None = None,
    page_separator: str = "\n\n",
) -> PDFDocument:
    """Read and extract text, pages, and metadata from a PDF."""
    if isinstance(source, (str, Path)):
        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a regular file: {file_path}")

        source_name = str(file_path.resolve())
        with open(file_path, "rb") as file_stream:
            return _parse_pdf_stream(
                stream=file_stream,
                source_name=source_name,
                password=password,
                page_separator=page_separator,
            )

    if isinstance(source, (bytes, bytearray)):
        return _parse_pdf_stream(
            stream=io.BytesIO(source),
            source_name="in-memory-bytes",
            password=password,
            page_separator=page_separator,
        )

    if hasattr(source, "read"):
        source_name = getattr(source, "name", "binary-stream")
        return _parse_pdf_stream(
            stream=source,
            source_name=source_name,
            password=password,
            page_separator=page_separator,
        )

    raise TypeError(
        f"Unsupported PDF source type '{type(source).__name__}'. "
        "Expected str, Path, bytes, or binary stream."
    )


def read_pdf_text(
    source: str | Path | bytes | BinaryIO,
    password: str | None = None,
    page_separator: str = "\n\n",
) -> str:

    doc = read_pdf(source=source, password=password, page_separator=page_separator)
    return doc.text


def read_pdf_as_documents(
    source: str | Path | bytes | BinaryIO,
    password: str | None = None,
) -> list[Document]:
   
    pdf_doc = read_pdf(source=source, password=password)
    documents: list[Document] = []

    for page in pdf_doc.pages:
        page_metadata = {
            **pdf_doc.metadata,
            "source": pdf_doc.source,
            "page": page.page_number,
            "total_pages": pdf_doc.total_pages,
        }
        documents.append(
            Document(
                page_content=page.text,
                metadata=page_metadata,
            )
        )

    return documents    
