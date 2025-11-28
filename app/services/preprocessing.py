"""
Document preprocessing utilities for text extraction and chunking.
"""

import pdfplumber
import docx2txt
from typing import List
from loguru import logger


def process_document(file_path: str) -> str:
    """
    Extract text from various document formats.

    Args:
        file_path: Path to the document file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is not supported
    """
    file_lower = file_path.lower()

    try:
        if file_lower.endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        elif file_lower.endswith('.docx'):
            return extract_text_from_docx(file_path)
        elif file_lower.endswith('.txt'):
            return extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    except Exception as e:
        logger.error(f"Failed to process document {file_path}: {e}")
        raise


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    return docx2txt.process(file_path)


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_text(
    text: str,
    min_size: int = 300,
    max_size: int = 1200,
    overlap: int = 100
) -> List[str]:
    """
    Split text into overlapping chunks with semantic awareness for better context retrieval.

    Enhanced strategy:
    - Respects paragraph boundaries
    - Maintains semantic coherence
    - Ensures minimum chunk size for context
    - Adds smart overlap to preserve continuity
    - Handles section headers and special formatting

    Args:
        text: Input text to chunk
        min_size: Minimum chunk size in characters
        max_size: Maximum chunk size in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of text chunks with preserved context
    """
    # Clean and normalize text
    text = text.strip()

    # Split by double newlines (paragraphs) but preserve single newlines
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    # If no paragraph breaks, try single newlines
    if len(paragraphs) == 1:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    chunks = []
    current_chunk = ""
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        # Check if this paragraph is a section header (short, possibly numbered/titled)
        is_header = (para_size < 100 and
                     (para.isupper() or
                      any(para.startswith(prefix) for prefix in ['Section', 'Chapter', 'Article', 'SECTION', 'CHAPTER']) or
                      (para[0].isdigit() and '.' in para[:5])))

        # If adding this paragraph would exceed max_size
        if current_size + para_size > max_size and current_size >= min_size:
            # Save current chunk
            chunks.append(current_chunk.strip())

            # Start new chunk with smart overlap
            # If previous chunk ends with header, include it in new chunk
            overlap_text = current_chunk[-overlap:
                                         ] if not is_header else current_chunk[-overlap*2:]
            current_chunk = overlap_text + "\n\n" + para
            current_size = len(current_chunk)
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
            current_size = len(current_chunk)

    # Add the last chunk
    if current_chunk.strip() and len(current_chunk.strip()) >= min_size // 2:
        chunks.append(current_chunk.strip())

    # Handle chunks that are still too large - split by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_size:
            final_chunks.append(chunk)
        else:
            # Split by sentences (multiple patterns for better accuracy)
            import re
            # Split on period followed by space and capital, or period at end
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', chunk)

            temp_chunk = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # If adding this sentence exceeds max, save current
                if len(temp_chunk) + len(sentence) + 2 > max_size and len(temp_chunk) >= min_size:
                    final_chunks.append(temp_chunk.strip())
                    # Start new with overlap
                    last_sentences = temp_chunk.split(
                        '. ')[-2:] if '. ' in temp_chunk else []
                    temp_chunk = '. '.join(
                        last_sentences) + ". " + sentence if last_sentences else sentence
                else:
                    temp_chunk += " " + sentence if temp_chunk else sentence

            # Add remaining
            if temp_chunk.strip() and len(temp_chunk.strip()) >= min_size // 2:
                final_chunks.append(temp_chunk.strip())

    # Remove any chunks that are too short (likely artifacts)
    final_chunks = [c for c in final_chunks if len(c.strip()) >= min_size // 2]

    # Ensure we have at least one chunk
    if not final_chunks and text:
        final_chunks = [text[:max_size]]

    logger.info(
        f"Created {len(final_chunks)} semantic chunks from text (avg size: {sum(len(c) for c in final_chunks) // max(len(final_chunks), 1)} chars)")
    return final_chunks
