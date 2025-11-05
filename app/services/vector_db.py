"""
ChromaDB vector database for document embeddings and semantic search.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import settings


class ChromaDB:
    """ChromaDB client singleton for vector storage and retrieval."""

    client = None
    collection = None
    embedding_model = None

    @classmethod
    def initialize(cls):
        """Initialize ChromaDB client and embedding model."""
        try:
            cls.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            cls.collection = cls.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )

            cls.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE
            )

            logger.info(
                f"ChromaDB initialized with {cls.collection.count()} embeddings"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @classmethod
    def add_documents(
        cls,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents to ChromaDB with embeddings.

        Args:
            texts: List of text chunks
            metadatas: List of metadata dictionaries
            ids: List of unique IDs for chunks
        """
        try:
            embeddings = cls.embedding_model.encode(
                texts,
                show_progress_bar=False
            ).tolist()

            cls.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(texts)} documents to ChromaDB")

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    @classmethod
    def search(
        cls,
        query_text: str,
        n_results: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents using semantic search.

        Args:
            query_text: The search query
            n_results: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            Dictionary with search results
        """
        try:
            query_embedding = cls.embedding_model.encode(
                [query_text],
                show_progress_bar=False
            ).tolist()

            results = cls.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=filter_dict
            )

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    @classmethod
    def get_collection_count(cls) -> int:
        """Get the total number of embeddings in the collection."""
        return cls.collection.count()

    @classmethod
    def delete_by_doc_id(cls, doc_id: str):
        """
        Delete all chunks for a specific document.

        Args:
            doc_id: The document ID to delete
        """
        try:
            cls.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted chunks for document: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise


# Initialize on module import
ChromaDB.initialize()
