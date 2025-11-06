"""
ChromaDB vector database for document embeddings and semantic search.
Enhanced with LLM-powered query understanding and multi-strategy retrieval.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from loguru import logger
from groq import Groq
import asyncio

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
    seq_ratio = difflib.SequenceMatcher(
        None, normalize_text(query), normalize_text(text)).ratio()

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
    fillers = {"the", "a", "an", "that", "this", "these",
               "those", "was", "is", "are", "be", "been", "just"}
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


def llm_expand_query(query: str) -> Dict[str, Any]:
    """
    Use LLM to intelligently expand the query with:
    1. Semantic variations
    2. Key concepts to search for
    3. Potential exclusions/negations to check
    4. Hypothetical answer snippet (HyDE technique)

    This dramatically improves retrieval accuracy by understanding user intent.
    """
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        expansion_prompt = f"""You are a search query analyzer for an insurance document RAG system. Analyze this user query and help improve document retrieval.

USER QUERY: "{query}"

Provide a JSON response with:
1. "semantic_variants": 3-5 rephrased versions capturing the same intent
2. "key_concepts": Important keywords/phrases to search for
3. "exclusion_terms": Related terms about what's NOT covered (exclusions, limitations)
4. "hypothetical_answer": A 2-sentence example of what a relevant document passage might say

Focus on insurance terminology, coverage/exclusions, and policy language.

Respond ONLY with valid JSON:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a search optimization expert for insurance documents. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": expansion_prompt
                }
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        import json
        expansion = json.loads(response.choices[0].message.content)
        logger.info(
            f"LLM query expansion: {len(expansion.get('semantic_variants', []))} variants generated")
        return expansion

    except Exception as e:
        logger.warning(f"LLM query expansion failed, using fallback: {e}")
        # Fallback to basic expansion
        return {
            "semantic_variants": [query],
            "key_concepts": tokenize(query),
            "exclusion_terms": [],
            "hypothetical_answer": ""
        }


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
        filter_dict: Optional[Dict[str, Any]] = None,
        use_llm_expansion: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced search with LLM-powered query understanding and multi-strategy retrieval.

        Strategy:
        1. Use LLM to expand query into semantic variants + key concepts
        2. Retrieve more candidates using multiple query versions
        3. Apply hybrid scoring (semantic + lexical + LLM relevance)
        4. Return top results after intelligent reranking
        """
        try:
            # Step 1: LLM-powered query expansion
            expansion = llm_expand_query(query_text) if use_llm_expansion else {
                "semantic_variants": [query_text],
                "key_concepts": tokenize(query_text),
                "exclusion_terms": [],
                "hypothetical_answer": ""
            }

            # Step 2: Multi-query retrieval - search with original + variants
            all_candidates = {}  # Use dict to deduplicate by chunk ID

            # Search with original query
            initial_results = cls.search(
                query_text,
                n_results=retrieve_count,
                filter_dict=filter_dict
            )

            if initial_results['documents'][0]:
                for i, chunk_id in enumerate(initial_results['ids'][0]):
                    if chunk_id not in all_candidates:
                        all_candidates[chunk_id] = {
                            'document': initial_results['documents'][0][i],
                            'metadata': initial_results['metadatas'][0][i],
                            'id': chunk_id,
                            'distance': initial_results['distances'][0][i],
                            'query_matches': [query_text]
                        }
                    else:
                        all_candidates[chunk_id]['query_matches'].append(
                            query_text)

            # Search with semantic variants
            for variant in expansion.get('semantic_variants', [])[:3]:  # Limit to top 3
                if variant.lower() == query_text.lower():
                    continue

                try:
                    variant_results = cls.search(
                        variant,
                        n_results=retrieve_count // 2,  # Fewer results per variant
                        filter_dict=filter_dict
                    )

                    if variant_results['documents'][0]:
                        for i, chunk_id in enumerate(variant_results['ids'][0]):
                            if chunk_id not in all_candidates:
                                all_candidates[chunk_id] = {
                                    'document': variant_results['documents'][0][i],
                                    'metadata': variant_results['metadatas'][0][i],
                                    'id': chunk_id,
                                    'distance': variant_results['distances'][0][i],
                                    'query_matches': [variant]
                                }
                            else:
                                all_candidates[chunk_id]['query_matches'].append(
                                    variant)
                except Exception as e:
                    logger.warning(
                        f"Variant search failed for '{variant}': {e}")

            # Search with hypothetical answer (HyDE technique)
            hyde_text = expansion.get('hypothetical_answer', '')
            if hyde_text and len(hyde_text) > 20:
                try:
                    hyde_results = cls.search(
                        hyde_text,
                        n_results=retrieve_count // 2,
                        filter_dict=filter_dict
                    )

                    if hyde_results['documents'][0]:
                        for i, chunk_id in enumerate(hyde_results['ids'][0]):
                            if chunk_id not in all_candidates:
                                all_candidates[chunk_id] = {
                                    'document': hyde_results['documents'][0][i],
                                    'metadata': hyde_results['metadatas'][0][i],
                                    'id': chunk_id,
                                    'distance': hyde_results['distances'][0][i],
                                    'query_matches': ['[HyDE]']
                                }
                            else:
                                all_candidates[chunk_id]['query_matches'].append(
                                    '[HyDE]')
                except Exception as e:
                    logger.warning(f"HyDE search failed: {e}")

            if not all_candidates:
                return initial_results

            # Step 3: Advanced hybrid scoring
            key_concepts = set(expansion.get('key_concepts', []))
            exclusion_terms = set(expansion.get('exclusion_terms', []))

            scored_results = []
            for chunk_id, candidate in all_candidates.items():
                doc = candidate['document']
                distance = candidate['distance']

                # 1. Semantic similarity score (from embedding distance)
                semantic_score = 1.0 - distance

                # 2. Lexical matching with query + variants
                variants = [query_text] + generate_query_variants(query_text)
                lexical_scores = [calculate_lexical_score(
                    v, doc) for v in variants]
                keyword_score = max(lexical_scores) if lexical_scores else 0.0

                # 3. Key concept coverage bonus
                doc_tokens = set(tokenize(doc))
                concept_matches = key_concepts.intersection(doc_tokens)
                concept_score = len(
                    concept_matches) / max(len(key_concepts), 1) if key_concepts else 0.0

                # 4. Exclusion term bonus (insurance documents often describe exclusions)
                exclusion_matches = exclusion_terms.intersection(doc_tokens)
                exclusion_score = len(
                    exclusion_matches) / max(len(exclusion_terms), 1) if exclusion_terms else 0.0

                # 5. Multi-query match bonus (found by multiple search strategies)
                multi_match_bonus = min(
                    len(candidate['query_matches']) * 0.05, 0.15)

                # Combined scoring with weights
                combined_score = (
                    0.45 * semantic_score +      # Embedding similarity
                    0.20 * keyword_score +        # Lexical overlap
                    0.15 * concept_score +        # Key concept coverage
                    0.10 * exclusion_score +      # Exclusion term presence
                    0.10 * multi_match_bonus      # Multi-strategy confidence
                )

                scored_results.append({
                    'score': combined_score,
                    'document': doc,
                    'metadata': candidate['metadata'],
                    'id': chunk_id,
                    'distance': distance,
                    'debug': {
                        'semantic': semantic_score,
                        'lexical': keyword_score,
                        'concepts': concept_score,
                        'exclusions': exclusion_score,
                        'multi_match': multi_match_bonus
                    }
                })

            # Step 4: Sort and return top results
            scored_results.sort(key=lambda x: x['score'], reverse=True)
            top_results = scored_results[:n_results]

            reranked = {
                'documents': [[r['document'] for r in top_results]],
                'metadatas': [[r['metadata'] for r in top_results]],
                'ids': [[r['id'] for r in top_results]],
                'distances': [[r['distance'] for r in top_results]]
            }

            logger.info(
                f"Enhanced retrieval: {len(all_candidates)} candidates → top {n_results} "
                f"(concepts: {len(key_concepts)}, exclusions: {len(exclusion_terms)})"
            )
            return reranked

        except Exception as e:
            logger.error(
                f"Enhanced search failed, falling back to basic search: {e}")
            # Fallback to basic search
            return cls.search(query_text, n_results=n_results, filter_dict=filter_dict)

    @classmethod
    def get_collection_count(cls) -> int:
        """Get the total number of embeddings in the collection."""
        return cls.collection.count()

    @classmethod
    def get_user_documents(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific user.

        Args:
            user_id: The user ID to filter by

        Returns:
            List of documents with metadata
        """
        try:
            # Query all documents for this user
            results = cls.collection.get(
                where={"user_id": user_id},
                include=["metadatas"]
            )

            if not results or not results['metadatas']:
                return []

            # Group chunks by doc_id
            docs_dict = {}
            for metadata in results['metadatas']:
                doc_id = metadata.get('doc_id')
                if doc_id and doc_id not in docs_dict:
                    docs_dict[doc_id] = {
                        'doc_id': doc_id,
                        'filename': metadata.get('filename', 'Unknown'),
                        'upload_date': metadata.get('upload_date'),
                        'user_id': metadata.get('user_id'),
                        'chunk_count': 0
                    }

                if doc_id:
                    docs_dict[doc_id]['chunk_count'] += 1

            # Convert to list and sort by upload date (newest first)
            documents = list(docs_dict.values())
            documents.sort(
                key=lambda x: x.get('upload_date', ''),
                reverse=True
            )

            logger.info(
                f"Retrieved {len(documents)} documents for user {user_id}")
            return documents

        except Exception as e:
            logger.error(f"Failed to get user documents: {e}")
            return []

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

    @classmethod
    def delete_all_documents(cls):
        """
        Delete ALL documents and chunks from the collection.
        WARNING: This will clear the entire vector database!
        """
        try:
            # Get all IDs
            all_data = cls.collection.get()
            if all_data and all_data['ids']:
                count = len(all_data['ids'])
                cls.collection.delete(ids=all_data['ids'])
                logger.info(f"Deleted all {count} chunks from ChromaDB")
                return count
            else:
                logger.info("No documents to delete")
                return 0
        except Exception as e:
            logger.error(f"Failed to delete all documents: {e}")
            raise


# Initialize on module import
ChromaDB.initialize()
