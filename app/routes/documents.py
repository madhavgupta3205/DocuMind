"""
Document upload and management routes.
Protected by JWT authentication and rate limiting.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import uuid
from datetime import datetime
from loguru import logger

from app.middleware.auth_middleware import get_current_user
from app.models.user import TokenData
from app.services.vector_db import ChromaDB
from app.services.preprocessing import process_document, chunk_text
from app.config import settings

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/upload")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Upload and process a document for RAG querying.

    Protected by JWT authentication and rate limiting.

    Args:
        request: FastAPI request (for rate limiting)
        file: Uploaded document file
        current_user: Authenticated user

    Returns:
        Upload confirmation with document ID

    Raises:
        HTTPException: If file processing fails
    """
    try:
        # Validate file size
        contents = await file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Generate unique document ID
        doc_id = f"{current_user.user_id}_{uuid.uuid4().hex[:12]}"

        # Save file
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(
            settings.UPLOAD_DIR, f"{doc_id}_{file.filename}")

        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(f"File saved: {file_path}")

        # Process document
        text = process_document(file_path)

        if not text or len(text.strip()) < 100:
            raise HTTPException(
                status_code=400,
                detail="Document contains insufficient text content"
            )

        # Chunk text
        chunks = chunk_text(
            text,
            min_size=settings.MIN_CHUNK_SIZE,
            max_size=settings.MAX_CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )

        logger.info(f"Generated {len(chunks)} chunks from document")

        # Prepare for ChromaDB
        chunk_ids = []
        chunk_texts = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "filename": file.filename,
                "user_id": current_user.user_id,
                "upload_date": datetime.utcnow().isoformat(),
                "chunk_index": i
            })

        # Add to ChromaDB
        ChromaDB.add_documents(
            texts=chunk_texts,
            metadatas=metadatas,
            ids=chunk_ids
        )

        logger.info(f"Document processed successfully: {doc_id}")

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks_created": len(chunks),
            "message": "Document uploaded and processed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a document and all its chunks.

    Args:
        doc_id: Document ID to delete
        current_user: Authenticated user

    Returns:
        Deletion confirmation
    """
    try:
        # Verify ownership by checking if doc_id starts with user_id
        if not doc_id.startswith(current_user.user_id):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to delete this document"
            )

        ChromaDB.delete_by_doc_id(doc_id)

        logger.info(f"Document deleted: {doc_id}")

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Document deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/stats")
async def get_stats(current_user: TokenData = Depends(get_current_user)):
    """
    Get document statistics for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        Document statistics
    """
    total_embeddings = ChromaDB.get_collection_count()

    return {
        "total_embeddings": total_embeddings,
        "user_id": current_user.user_id
    }


@router.get("/list")
async def list_documents(current_user: TokenData = Depends(get_current_user)):
    """
    List all documents for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of user documents with metadata
    """
    try:
        user_docs = ChromaDB.get_user_documents(current_user.user_id)

        return {
            "success": True,
            "documents": user_docs,
            "total": len(user_docs)
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )
