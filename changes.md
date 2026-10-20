# Change Log

This file records important code, configuration, dependency, schema, security, and deployment changes. Every code entry should include verified one-based line numbers from the final saved files.

## Entry template

```markdown
## YYYY-MM-DD - Short change title

- **Reason:** Why the change was needed.
- **Files changed:**
  - `path/to/file.py`
    - Lines 10-28: Describe the important change and affected function/class.
  - `tests/test_file.py`
    - Lines 15-39: Describe the test coverage added.
- **Impact:** Compatibility, security, data, or operational implications.
- **Validation:** Commands actually run and results.
- **Follow-up:** Remaining work, or `None`.
```

## Initial project documentation

- **Status:** Initial project documentation created.
- **Files:** `AGENTS.md`, `PRD.md`, `TRD.md`, `requirements.txt`.
- **Code change line references:** Not applicable. No application source code was changed by creating these project documentation files.
- **Validation:** File creation verified. Dependency installation, compatibility resolution, and application tests have not been run.
- **Follow-up:** Implement the project foundation and record each meaningful source-code change with verified line ranges.

## 2026-10-20 - Implement PDF reading and document extraction functions

- **Reason:** Provide robust, enterprise-grade PDF reading and document extraction capabilities for document ingestion in ResearchOS.
- **Files changed:**
  - `backend/src/loaders/document_loader.py`
    - Lines 17-19: Added custom exception `PDFReadError`.
    - Lines 21-27: Added Pydantic schema `PDFPage` representing extracted page text, page index, and char count.
    - Lines 29-46: Added Pydantic schema `PDFDocument` representing parsed document structure, metadata, page list, and full concatenated text.
    - Lines 48-60: Added `_clean_pdf_metadata` to normalize raw PDF metadata dictionary keys and values.
    - Lines 62-124: Added `_parse_pdf_stream` to parse binary PDF streams, handle encrypted/password-protected PDFs, extract text per page defensively, and log structured metrics.
    - Lines 126-169: Added primary `read_pdf` function supporting file paths (`str` or `Path`), raw `bytes`, or binary streams with safe file context management.
    - Lines 171-188: Added `read_pdf_text` convenience function returning full extracted text string.
    - Lines 190-226: Added `read_pdf_as_documents` returning LangChain `Document` objects with page-level and document-level metadata for RAG ingestion.
  - `backend/src/loaders/__init__.py`
    - Lines 1-17: Exported `read_pdf`, `read_pdf_text`, `read_pdf_as_documents`, `PDFDocument`, `PDFPage`, `PDFReadError`.
  - `backend/tests/test_document_loader.py`
    - Lines 1-154: Added 10 unit test cases covering reading bytes, file paths, streams, text convenience, LangChain Document conversion, metadata extraction, missing files, corrupted data, invalid types, and password encryption handling.
- **Impact:** Enables ingestion of PDF research papers, reports, and enterprise documents from disk or upload streams. Non-breaking additive functionality.
- **Validation:**
  - `.\.venv\Scripts\pytest tests/test_document_loader.py -v`: 10 passed in 0.35s.
  - `.\.venv\Scripts\ruff check src/loaders tests/test_document_loader.py`: All checks passed.
- **Follow-up:** Connect PDF loader to text splitter and embedding/vector indexing pipeline in `TASK-013`.

## 2026-10-20 - Add resilient web data loader and general HTML content parser

- **Reason:** Provide web scraping and HTML content parsing capabilities for web article and page ingestion in ResearchOS.
- **Files changed:**
  - `backend/requirements.txt`
    - Line 67: Added `fake-useragent` dependency for randomized user-agent rotation.
  - `backend/src/loaders/web_data_loader.py`
    - Lines 13-46: Implemented `ScraperSession` with session pooling, `urllib3` retry backoff strategy for HTTP 429/5xx status codes, random User-Agent headers, polite jitter delay, and request error logging.
    - Lines 48-75: Implemented `parse_data` to strip non-content elements (`<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`), extract page title, and aggregate clean readable text across headings and body paragraphs.
  - `backend/src/loaders/__init__.py`
    - Lines 10-13, 22-23: Exported `ScraperSession` and `parse_data` from `src.loaders`.
  - `backend/src/loaders/document_loader.py`
    - Lines 126-203: Streamlined function signatures and return flow for PDF document loaders.
- **Impact:** Enables automated scraping and clean textual extraction from external web pages, research blogs, and news sources with network failure resilience.
- **Validation:** Verified via `python test/web_test.py` successfully fetching and parsing target web content with HTTP retry handling and clean text extraction.
- **Follow-up:** Add unit tests for `ScraperSession` and integrate parsed web text into the chunking pipeline.


