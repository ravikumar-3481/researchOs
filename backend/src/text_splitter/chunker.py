
from __future__ import annotations
import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable
from src.utils import TextCleaner


@dataclass
class PageContent:
    page_number: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextChunk:
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    page_end: int
    chunk_index: int
    token_count: int
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HybridChunker:
    def __init__(
        self,
        target_tokens: int = 500,
        max_tokens: int = 700,
        min_tokens: int = 50,
        overlap_sentences: int = 1,
        token_counter: Callable[[str], int] | None = None,
    ) -> None:
        if min_tokens < 1:
            raise ValueError("min_tokens must be at least 1.")

        if target_tokens < min_tokens:
            raise ValueError(
                "target_tokens must be >= min_tokens."
            )

        if max_tokens < target_tokens:
            raise ValueError(
                "max_tokens must be >= target_tokens."
            )

        if overlap_sentences < 0:
            raise ValueError(
                "overlap_sentences cannot be negative."
            )

        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_sentences = overlap_sentences
        self.token_counter = (
            token_counter or self._estimate_tokens
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate tokens when no model tokenizer is supplied."""
        return len(
            re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaner = TextCleaner()
        return cleaner.clean_data(text)

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        return [
            part.strip()
            for part in re.split(r"\n\s*\n", text)
            if part.strip()
        ]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """A practical sentence splitter for general prose."""
        text = text.strip()
        if not text:
            return []

        # Protect common abbreviations from accidental splitting.
        protected = text
        abbreviations = {
            "Mr.": "Mr<prd>",
            "Mrs.": "Mrs<prd>",
            "Ms.": "Ms<prd>",
            "Dr.": "Dr<prd>",
            "Prof.": "Prof<prd>",
            "e.g.": "e<prd>g<prd>",
            "i.e.": "i<prd>e<prd>",
            "vs.": "vs<prd>",
            "etc.": "etc<prd>",
        }

        for original, replacement in abbreviations.items():
            protected = re.sub(
                re.escape(original),
                replacement,
                protected,
                flags=re.IGNORECASE,
            )

        parts = re.split(
            r'(?<=[.!?])["\']?\s+(?=[A-Z0-9"\'(])',
            protected,
        )

        return [
            part.replace("<prd>", ".").strip()
            for part in parts
            if part.strip()
        ]

    def _split_long_sentence(self, text: str) -> list[str]:
        """Split unusually long sentences without losing their words."""
        words = text.split()
        parts: list[str] = []
        current: list[str] = []

        for word in words:
            candidate = " ".join(current + [word])

            if (
                current
                and self.token_counter(candidate) > self.max_tokens
            ):
                parts.append(" ".join(current))
                current = [word]
            else:
                current.append(word)

        if current:
            parts.append(" ".join(current))

        return parts

    def _split_long_paragraph(
        self, paragraph: str
    ) -> list[str]:
        sentences = self._split_sentences(paragraph)
        if not sentences:
            return []

        result: list[str] = []
        current: list[str] = []

        for sentence in sentences:
            if self.token_counter(sentence) > self.max_tokens:
                if current:
                    result.append(" ".join(current))
                    current = []

                result.extend(
                    self._split_long_sentence(sentence)
                )
                continue

            candidate = " ".join(current + [sentence])

            if (
                current
                and self.token_counter(candidate) > self.target_tokens
            ):
                result.append(" ".join(current))
                current = [sentence]
            else:
                current.append(sentence)

        if current:
            result.append(" ".join(current))

        return result

    def _make_page_chunks(
        self, page: PageContent
    ) -> list[str]:
        text = self._clean_text(page.text)
        if not text:
            return []

        paragraphs = self._split_paragraphs(text)
        chunks: list[str] = []
        current: list[str] = []

        for paragraph in paragraphs:
            paragraph_tokens = self.token_counter(paragraph)

            if paragraph_tokens > self.max_tokens:
                if current:
                    chunks.append("\n\n".join(current))
                    current = []

                chunks.extend(
                    self._split_long_paragraph(paragraph)
                )
                continue

            candidate = "\n\n".join(current + [paragraph])

            if (
                current
                and self.token_counter(candidate) > self.target_tokens
            ):
                chunks.append("\n\n".join(current))
                current = [paragraph]
            else:
                current.append(paragraph)

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def chunk_document(
        self,
        document_id: str,
        pages: Iterable[PageContent],
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        if not document_id or not document_id.strip():
            raise ValueError("document_id cannot be empty.")

        # Stable page order, with page boundaries preserved.
        ordered_pages = sorted(
            pages, key=lambda page: page.page_number
        )

        if any(page.page_number < 1 for page in ordered_pages):
            raise ValueError("Page numbers must start at 1.")

        page_numbers = [
            page.page_number for page in ordered_pages
        ]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("Duplicate page numbers detected.")

        document_metadata = document_metadata or {}
        raw_chunks: list[tuple[str, PageContent]] = []

        for page in ordered_pages:
            for text in self._make_page_chunks(page):
                if text.strip():
                    raw_chunks.append((text, page))

        results: list[TextChunk] = []

        for index, (text, page) in enumerate(raw_chunks):
            normalized = self._clean_text(text)
            content_hash = hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest()

            # IDs remain stable if the same ordered content is processed.
            chunk_id = hashlib.sha256(
                f"{document_id}:{page.page_number}:{index}:"
                f"{content_hash}".encode("utf-8")
            ).hexdigest()

            results.append(
                TextChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=normalized,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    chunk_index=index,
                    token_count=self.token_counter(normalized),
                    content_hash=content_hash,
                    metadata={
                        **document_metadata,
                        **page.metadata,
                    },
                )
            )

        if self.overlap_sentences > 0:
            for index in range(1, len(results)):
                previous = results[index - 1]
                current = results[index]

                if previous.page_end != current.page_start:
                    continue

                previous_sentences = self._split_sentences(
                    previous.text
                )
                current_text = current.text

                overlap = previous_sentences[
                    -self.overlap_sentences:
                ]

                if not overlap:
                    continue

                prefix = " ".join(overlap)
                candidate = prefix + " " + current_text

                if (
                    self.token_counter(candidate) <= self.max_tokens
                    and prefix not in current_text
                ):
                    current.text = candidate
                    current.token_count = self.token_counter(
                        current.text
                    )

                    current.content_hash = hashlib.sha256(
                        current.text.encode("utf-8")
                    ).hexdigest()

                    current.chunk_id = hashlib.sha256(
                        f"{current.document_id}:"
                        f"{current.page_start}:"
                        f"{current.chunk_index}:"
                        f"{current.content_hash}".encode("utf-8")
                    ).hexdigest()

        return results
