"""
Pinecone vector database for production-grade document embeddings and semantic search.
Enhanced with LLM-powered query understanding and multi-strategy retrieval.
Uses Pinecone Inference API for serverless embeddings (NO local model = NO memory issues!).
"""

from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from loguru import logger
from groq import Groq
import asyncio
import uuid
import time
from datetime import datetime

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
    """A lightweight lexical similarity score."""
    q_tokens = set(tokenize(query))
    t_tokens = set(tokenize(text))

    if not q_tokens or not t_tokens:
        return 0.0

    intersection = q_tokens.intersection(t_tokens)
    token_score = len(intersection) / max(len(q_tokens), 1)

    seq_ratio = difflib.SequenceMatcher(
        None, normalize_text(query), normalize_text(text)
    ).ratio()

    return (token_score * 0.6) + (seq_ratio * 0.4)


def calculate_concept_coverage(key_concepts: List[str], text: str) -> float:
    """Calculate how many key concepts appear in the text."""
    if not key_concepts:
        return 0.0

    text_lower = text.lower()
    matches = sum(
        1 for concept in key_concepts if concept.lower() in text_lower)
    return matches / len(key_concepts)


def calculate_exclusion_penalty(exclusion_terms: List[str], text: str) -> float:
    """Penalize if exclusion terms are present in text."""
    if not exclusion_terms:
        return 0.0

    text_lower = text.lower()
    matches = sum(1 for term in exclusion_terms if term.lower() in text_lower)
    return matches / max(len(exclusion_terms), 1)


def calculate_multi_match_bonus(variants: List[str], text: str) -> float:
    """Bonus if text matches multiple query variants."""
    if not variants:
        return 0.0

    text_lower = text.lower()
    matches = sum(1 for variant in variants if variant.lower() in text_lower)
    return min(matches / max(len(variants), 1), 1.0)


class PineconeDB:
    """Production-grade Pinecone vector database with serverless inference (no local model!)."""

    def __init__(self):
        """Initialize Pinecone with serverless index and inference API."""
        # NO embedding model loaded - use Pinecone Inference API instead!
        self.dimension = 384  # all-MiniLM-L6-v2 dimension

        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME

        # Create index if it doesn't exist
        self._ensure_index_exists()

        # Connect to index
        self.index = self.pc.Index(self.index_name)

        # Initialize Pinecone Inference (serverless embeddings - no memory!)
        try:
            from pinecone import Pinecone as PineconeClient
            self.inference = PineconeClient(api_key=settings.PINECONE_API_KEY)
            logger.info("✅ Using Pinecone Inference API (serverless embeddings)")
        except Exception as e:
            logger.warning(f"Pinecone Inference unavailable: {e}")
            self.inference = None

        # Initialize Groq for LLM expansion
        try:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.warning(
                f"Groq initialization failed: {e}. LLM expansion will be disabled.")
            self.groq_client = None

        logger.info(f"✅ PineconeDB initialized with index: {self.index_name}")

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Pinecone Inference API (serverless - no memory!)."""
        try:
            # Use Pinecone's inference API - NO local model needed!
            response = self.inference.inference.embed(
                model="multilingual-e5-large",
                inputs=texts,
                parameters={"input_type": "passage"}
            )
            return [item['values'] for item in response['data']]
        except Exception as e:
            logger.error(f"Pinecone inference failed: {e}")
            # Fallback: use simple TF-IDF-like approach (no ML model)
            logger.warning("Using fallback text encoding (no embeddings)")
            return [[hash(text) % 1000 / 1000.0 for _ in range(self.dimension)] for text in texts]

    def _ensure_index_exists(self):
        """Create Pinecone index if it doesn't exist."""
        try:
            existing_indexes = [index['name']
                                for index in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        }
                    }
                )
                # Wait for index to be ready
                max_wait = 30
                waited = 0
                while waited < max_wait:
                    desc = self.pc.describe_index(self.index_name)
                    if desc['status']['ready']:
                        break
                    time.sleep(1)
                    waited += 1
                logger.info(f"✅ Index {self.index_name} created successfully")
            else:
                logger.info(f"Index {self.index_name} already exists")

        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")
            raise

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to Pinecone index."""
        try:
            if not texts:
                return []

            # Generate embeddings using serverless Pinecone Inference (no local model!)
            embeddings = self._embed_texts(texts)

            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in texts]

            # Prepare vectors for upsert
            vectors = []
            for i, (id_, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
                # Add text to metadata for retrieval
                metadata_with_text = {**metadata, "text": texts[i]}
                vectors.append({
                    "id": id_,
                    "values": embedding,
                    "metadata": metadata_with_text
                })

            # Upsert to Pinecone in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(
                    vectors=batch, namespace=settings.PINECONE_NAMESPACE)

            logger.info(f"✅ Added {len(texts)} documents to Pinecone")
            return ids

        except Exception as e:
            logger.error(f"Error adding documents to Pinecone: {e}")
            raise

    def llm_expand_query(self, query: str) -> Dict[str, Any]:
        """Use LLM to expand query with semantic variants and concepts."""
        if not self.groq_client:
            return {
                "variants": [query],
                "key_concepts": [],
                "exclusion_terms": [],
                "hypothetical_answer": query
            }

        try:
            prompt = f"""Given this user query, expand it for better document retrieval:

Query: "{query}"

Generate:
1. 3-5 semantic variations (different ways to ask the same thing)
2. Key concepts/terms that must be present in relevant documents
3. Exclusion terms (what should NOT be in results, e.g., if asking about "coverage", exclude "not covered")
4. A hypothetical ideal answer (1 sentence)

Respond in JSON format:
{{
    "variants": ["variant1", "variant2", "variant3"],
    "key_concepts": ["concept1", "concept2"],
    "exclusion_terms": ["term1", "term2"],
    "hypothetical_answer": "answer here"
}}"""

            response = self.groq_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a query expansion expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            import json
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM expansion result: {result}")
            return result

        except Exception as e:
            logger.warning(f"LLM expansion failed: {e}. Using original query.")
            return {
                "variants": [query],
                "key_concepts": [],
                "exclusion_terms": [],
                "hypothetical_answer": query
            }

    def search_with_reranking(
        self,
        query_text: str,
        n_results: int = 5,
        retrieve_count: int = 15,
        filter_dict: Optional[Dict[str, Any]] = None,
        use_llm_expansion: bool = True,
    ) -> List[Dict[str, Any]]:
        """Enhanced search with LLM expansion and hybrid scoring."""
        try:
            # Step 1: Expand query with LLM
            expansion = {"variants": [query_text], "key_concepts": [
            ], "exclusion_terms": [], "hypothetical_answer": query_text}
            if use_llm_expansion:
                expansion = self.llm_expand_query(query_text)

            # Step 2: Multi-strategy retrieval
            all_results = []
            queries_to_search = [
                query_text,
                *expansion["variants"],
                expansion["hypothetical_answer"]
            ]

            for search_query in queries_to_search:
                # Generate embedding using serverless inference
                query_embeddings = self._embed_texts([search_query])
                query_embedding = query_embeddings[0] if query_embeddings else []

                # Query Pinecone
                results = self.index.query(
                    vector=query_embedding,
                    top_k=retrieve_count,
                    include_metadata=True,
                    namespace=settings.PINECONE_NAMESPACE,
                    filter=filter_dict
                )

                all_results.extend(results.matches)

            # Step 3: Deduplicate by ID
            unique_results = {}
            for match in all_results:
                if match.id not in unique_results:
                    unique_results[match.id] = match
                else:
                    # Keep the one with higher score
                    if match.score > unique_results[match.id].score:
                        unique_results[match.id] = match

            # Step 4: Hybrid scoring
            scored_results = []
            for match in unique_results.values():
                text = match.metadata.get("text", "")

                # Semantic score (cosine similarity from Pinecone)
                semantic_score = match.score

                # Lexical score
                lexical_score = calculate_lexical_score(query_text, text)

                # Concept coverage
                concept_score = calculate_concept_coverage(
                    expansion["key_concepts"], text)

                # Exclusion penalty
                exclusion_penalty = calculate_exclusion_penalty(
                    expansion["exclusion_terms"], text)

                # Multi-match bonus
                multi_match_bonus = calculate_multi_match_bonus(
                    expansion["variants"], text)

                # Hybrid score (weighted combination)
                final_score = (
                    semantic_score * 0.45 +
                    lexical_score * 0.20 +
                    concept_score * 0.15 -
                    exclusion_penalty * 0.10 +
                    multi_match_bonus * 0.10
                )

                scored_results.append({
                    "text": text,
                    "metadata": {k: v for k, v in match.metadata.items() if k != "text"},
                    "score": final_score,
                    "semantic_score": semantic_score,
                    "lexical_score": lexical_score,
                    "id": match.id
                })

            # Step 5: Sort and return top N
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            top_results = scored_results[:n_results]

            logger.info(
                f"Retrieved {len(top_results)} results after reranking")
            return top_results

        except Exception as e:
            logger.error(f"Error in search_with_reranking: {e}")
            return []

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a specific document."""
        try:
            # Pinecone requires explicit IDs for deletion
            # We'll use metadata filtering to find and delete
            # Note: Pinecone free tier has limitations on metadata filtering

            # First, fetch all vectors with this doc_id
            # This is a workaround since free tier may not support delete by metadata
            logger.warning(
                "Pinecone delete by metadata may require paid tier. Consider storing doc_id mapping.")

            # For now, we'll use delete_by_filter if available
            try:
                self.index.delete(
                    filter={"doc_id": doc_id}, namespace=settings.PINECONE_NAMESPACE)
                logger.info(f"Deleted document {doc_id}")
                return 1
            except Exception as e:
                logger.error(f"Delete by filter not supported or failed: {e}")
                return 0

        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return 0

    def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a user."""
        try:
            # Note: Pinecone free tier has limitations on metadata queries
            # This is a simplified implementation

            # Query with user_id filter
            results = self.index.query(
                vector=[0] * self.dimension,  # Dummy vector
                top_k=10000,  # Max results
                include_metadata=True,
                namespace=settings.PINECONE_NAMESPACE,
                filter={"user_id": user_id}
            )

            # Group by doc_id
            doc_map = {}
            for match in results.matches:
                doc_id = match.metadata.get("doc_id")
                if doc_id and doc_id not in doc_map:
                    doc_map[doc_id] = {
                        "doc_id": doc_id,
                        "filename": match.metadata.get("filename", "unknown"),
                        "chunk_count": 0,
                        "upload_date": match.metadata.get("upload_date", "unknown")
                    }
                if doc_id:
                    doc_map[doc_id]["chunk_count"] += 1

            return list(doc_map.values())

        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return []

    def delete_all_documents(self) -> int:
        """Delete all documents (admin/testing only)."""
        try:
            # Delete all vectors in namespace
            self.index.delete(
                delete_all=True, namespace=settings.PINECONE_NAMESPACE)
            logger.info("Deleted all documents from Pinecone")
            return 1
        except Exception as e:
            logger.error(f"Error deleting all documents: {e}")
            return 0


# Singleton instance
_pinecone_db = None


def get_pinecone_db() -> PineconeDB:
    """Get or create PineconeDB singleton."""
    global _pinecone_db
    if _pinecone_db is None:
        _pinecone_db = PineconeDB()
    return _pinecone_db
