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
    Split text into overlapping chunks for better context retrieval.

    Args:
        text: Input text to chunk
        min_size: Minimum chunk size in characters
        max_size: Maximum chunk size in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph exceeds max_size, save current chunk
        if len(current_chunk) + len(para) > max_size and len(current_chunk) >= min_size:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            current_chunk = current_chunk[-overlap:] + " " + para
        else:
            current_chunk += " " + para if current_chunk else para

    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Handle case where chunks are still too large
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_size:
            final_chunks.append(chunk)
        else:
            # Split large chunks by sentences
            sentences = chunk.split('. ')
            temp_chunk = ""
            for sentence in sentences:
                if len(temp_chunk) + len(sentence) <= max_size:
                    temp_chunk += sentence + ". "
                else:
                    if temp_chunk:
                        final_chunks.append(temp_chunk.strip())
                    temp_chunk = sentence + ". "
            if temp_chunk:
                final_chunks.append(temp_chunk.strip())

    logger.info(f"Created {len(final_chunks)} chunks from text")
    return final_chunks
