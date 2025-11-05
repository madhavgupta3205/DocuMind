"""
ChromaDB vector database for document embeddings and semantic search.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import settings
import re
import difflib
import math


def normalize_text(s: str) -> str:
    """Lowercase, remove punctuation and collapse whitespace."""
    s = s or ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokenize(s: str) -> List[str]:
    return [t for t in normalize_text(s).split() if t]


def calculate_lexical_score(query: str, text: str) -> float:
    """A lightweight lexical similarity score.

    Combines token overlap (Jaccard-like) and difflib sequence ratio.
    Returns 0..1 float.
    """
    q_tokens = set(tokenize(query))
    t_tokens = set(tokenize(text))

    if not q_tokens or not t_tokens:
        return 0.0

    # token overlap
    intersection = q_tokens.intersection(t_tokens)
    token_score = len(intersection) / max(len(q_tokens), 1)

    # fuzzy sequence similarity on the raw normalized strings
    seq_ratio = difflib.SequenceMatcher(None, normalize_text(query), normalize_text(text)).ratio()

    # weighted combine, favoring token overlap
    return 0.7 * token_score + 0.3 * seq_ratio


def generate_query_variants(query: str) -> List[str]:
    """Create small set of query variants to help lexical matches.

    - original query
    - query without common filler words
    - joined tokens
    - (optionally) synonyms from WordNet if available
    This is intentionally small and lightweight to avoid heavy deps.
    """
    base = normalize_text(query)
    tokens = tokenize(query)
    fillers = {"the", "a", "an", "that", "this", "these", "those", "was", "is", "are", "be", "been", "just"}
    without_fillers = " ".join([t for t in tokens if t not in fillers])

    variants = [base]
    if without_fillers and without_fillers != base:
        variants.append(without_fillers)

    if tokens:
        variants.append(" ".join(tokens))
        variants.append("".join(tokens))

    # optional: attempt to use WordNet synonyms if nltk is present
    try:
        from nltk.corpus import wordnet as wn

        syns = set()
        for tok in tokens:
            for syn in wn.synsets(tok):
                for l in syn.lemmas():
                    syn_word = normalize_text(l.name().replace("_", " "))
                    if syn_word and syn_word not in tokens:
                        syns.add(syn_word)

        if syns:
            variants.extend(list(syns)[:6])
    except Exception:
        # nltk/wordnet not available — that's fine
        pass

    # dedupe while preserving order
    seen = set()
    out = []
    for v in variants:
        if v not in seen and v:
            seen.add(v)
            out.append(v)

    return out


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
        filter_dict: Optional[Dict[str, Any]] = None,
        use_expansion: bool = True
    ) -> Dict[str, Any]:
        try:
            # For now we keep the original query for embedding.
            # Query variants and lexical reranking are applied in search_with_reranking.
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
    def search_with_reranking(
        cls,
        query_text: str,
        n_results: int = 5,
        retrieve_count: int = 15,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            initial_results = cls.search(
                query_text,
                n_results=retrieve_count,
                filter_dict=filter_dict,
                use_expansion=True
            )
            
            if not initial_results['documents'][0]:
                return initial_results
            
            documents = initial_results['documents'][0]
            metadatas = initial_results['metadatas'][0]
            ids = initial_results['ids'][0]
            distances = initial_results['distances'][0]
            
            scored_results = []
            for i, doc in enumerate(documents):
                semantic_score = 1.0 - distances[i]

                # lexical score: consider small set of query variants and take the max
                variants = generate_query_variants(query_text)
                lexical_scores = [calculate_lexical_score(v, doc) for v in variants]
                keyword_score = max(lexical_scores) if lexical_scores else 0.0

                combined_score = (0.75 * semantic_score) + (0.25 * keyword_score)
                
                scored_results.append({
                    'score': combined_score,
                    'document': doc,
                    'metadata': metadatas[i],
                    'id': ids[i],
                    'distance': distances[i]
                })
            
            scored_results.sort(key=lambda x: x['score'], reverse=True)
            top_results = scored_results[:n_results]
            
            reranked = {
                'documents': [[r['document'] for r in top_results]],
                'metadatas': [[r['metadata'] for r in top_results]],
                'ids': [[r['id'] for r in top_results]],
                'distances': [[r['distance'] for r in top_results]]
            }
            
            logger.info(f"Re-ranked {retrieve_count} results to top {n_results}")
            return reranked
            
        except Exception as e:
            logger.error(f"Search with re-ranking failed: {e}")
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
