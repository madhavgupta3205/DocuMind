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
    """Advanced lexical similarity with BM25-inspired scoring.

    Combines:
    - Token overlap (Jaccard similarity)
    - BM25-like term frequency weighting
    - Phrase/bigram matching
    - Sequence similarity
    Returns 0..1 float.
    """
    q_tokens = tokenize(query)
    t_tokens = tokenize(text)
    q_token_set = set(q_tokens)
    t_token_set = set(t_tokens)

    if not q_token_set or not t_token_set:
        return 0.0

    # 1. Basic token overlap (Jaccard)
    intersection = q_token_set.intersection(t_token_set)
    jaccard = len(intersection) / max(len(q_token_set.union(t_token_set)), 1)

    # 2. BM25-inspired term frequency scoring
    # Penalize very common terms, boost rare exact matches
    tf_scores = []
    for q_term in q_tokens:
        if q_term in t_tokens:
            tf = t_tokens.count(q_term)
            # BM25-like saturation: tf / (tf + k1)
            k1 = 1.5
            tf_score = (tf * (k1 + 1)) / (tf + k1)
            tf_scores.append(tf_score)

    avg_tf_score = sum(tf_scores) / max(len(q_tokens), 1) if tf_scores else 0.0

    # 3. Phrase/bigram matching (important for multi-word terms)
    bigram_score = 0.0
    if len(q_tokens) >= 2:
        q_bigrams = set(zip(q_tokens[:-1], q_tokens[1:]))
        t_bigrams = set(zip(t_tokens[:-1], t_tokens[1:]))
        if q_bigrams and t_bigrams:
            bigram_matches = len(q_bigrams.intersection(t_bigrams))
            bigram_score = bigram_matches / len(q_bigrams)

    # 4. Fuzzy sequence similarity (catches minor variations)
    seq_ratio = difflib.SequenceMatcher(
        None, normalize_text(query), normalize_text(text)).ratio()

    # 5. Query coverage (what % of query terms found)
    query_coverage = len(intersection) / max(len(q_token_set), 1)

    # Weighted combination favoring exact matches and phrases
    combined = (
        0.25 * jaccard +           # Overall similarity
        0.25 * avg_tf_score +      # Term frequency importance
        0.20 * bigram_score +      # Phrase matching
        0.15 * query_coverage +    # Query term coverage
        0.15 * seq_ratio           # Fuzzy matching
    )

    return min(combined, 1.0)


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
    1. Semantic variations with domain synonyms
    2. Key concepts and technical terms
    3. Potential exclusions/negations to check
    4. Multiple hypothetical answers (HyDE technique)
    5. Question type classification

    This dramatically improves retrieval accuracy by understanding user intent.
    """
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        expansion_prompt = f"""You are an expert search query analyzer for document RAG systems, specializing in insurance, medical, and technical documents.

USER QUERY: "{query}"

Analyze this query deeply and provide a JSON response with:

1. "query_type": Classify as "definition", "coverage", "exclusion", "process", "eligibility", "comparison", or "general"

2. "semantic_variants": 5-7 high-quality rephrased versions that:
   - Use domain-specific terminology and synonyms
   - Include formal and informal variations
   - Cover different ways to ask the same question
   - Include related questions a user might actually ask

3. "key_concepts": List 8-12 critical keywords/phrases including:
   - Technical terms
   - Domain-specific vocabulary
   - Synonyms and abbreviations
   - Related concepts

4. "exclusion_terms": Terms related to limitations, restrictions, what's NOT covered:
   - "not covered", "excluded", "limitation", "restriction"
   - "does not apply", "not eligible", "not included"
   - Specific exclusion scenarios

5. "hypothetical_answers": Array of 2-3 example passages (2-3 sentences each) that would directly answer this query, written in formal document language

6. "context_hints": List of 4-6 section titles or document parts where this information would likely be found
   - E.g., "Coverage Details", "Exclusions", "Definitions", "Claims Process", etc.

Focus on insurance/medical terminology, coverage language, and policy structure.

IMPORTANT: Return ONLY valid JSON, no markdown or explanation:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert search optimization specialist for document retrieval systems. You understand insurance, medical, and legal terminology deeply. Always return valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": expansion_prompt
                }
            ],
            temperature=0.2,  # Lower temperature for more focused results
            max_tokens=800,  # More tokens for comprehensive expansion
            response_format={"type": "json_object"}
        )

        import json
        expansion = json.loads(response.choices[0].message.content)
        logger.info(
            f"LLM query expansion: type={expansion.get('query_type')}, "
            f"{len(expansion.get('semantic_variants', []))} variants, "
            f"{len(expansion.get('key_concepts', []))} concepts")
        return expansion

    except Exception as e:
        logger.warning(f"LLM query expansion failed, using fallback: {e}")
        # Enhanced fallback with basic domain synonyms
        domain_synonyms = {
            "baby": ["newborn", "infant", "neonate", "new born baby"],
            "child": ["minor", "dependent", "kid", "pediatric"],
            "coverage": ["benefit", "protection", "insurance", "policy coverage"],
            "excluded": ["not covered", "limitation", "restriction", "does not apply"],
            "treatment": ["medical care", "procedure", "therapy", "medical service"],
            "accident": ["accidental injury", "bodily injury", "external injury"],
            "claim": ["reimbursement", "payment request", "insurance claim"],
            "pre-existing": ["prior condition", "existing condition", "previous illness"]
        }

        expanded_terms = tokenize(query)
        query_lower = query.lower()
        for term, synonyms in domain_synonyms.items():
            if term in query_lower:
                expanded_terms.extend(synonyms)

        return {
            "query_type": "general",
            "semantic_variants": [query],
            "key_concepts": expanded_terms[:12],
            "exclusion_terms": ["not covered", "excluded", "limitation"],
            "hypothetical_answers": [query],
            "context_hints": ["Coverage", "Benefits", "Exclusions"]
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

            # Initialize embedding model with optimized settings
            import torch
            
            # Use all available CPU cores for faster encoding
            torch.set_num_threads(torch.get_num_threads())  # Ensure multi-threading is enabled
            
            cls.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE
            )
            
            # Enable additional optimizations
            cls.embedding_model.eval()  # Set to evaluation mode (faster inference)
            if settings.EMBEDDING_DEVICE == 'cpu':
                # Optimize for CPU inference
                import os
                os.environ['OMP_NUM_THREADS'] = str(torch.get_num_threads())
                os.environ['MKL_NUM_THREADS'] = str(torch.get_num_threads())

            logger.info(
                f"ChromaDB initialized with {cls.collection.count()} embeddings (using {torch.get_num_threads()} CPU threads)"
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
        Optimized with batch processing and multi-threading for faster uploads.

        Args:
            texts: List of text chunks
            metadatas: List of metadata dictionaries
            ids: List of unique IDs for chunks
        """
        try:
            import time
            start_time = time.time()
            
            logger.info(f"Starting embedding generation for {len(texts)} chunks...")
            
            # Generate embeddings with optimized settings
            # - batch_size: Process in optimal batches for better throughput
            # - normalize_embeddings: True for better similarity scoring (no quality loss)
            # - show_progress_bar: False to avoid overhead
            # - convert_to_numpy: True to get numpy arrays, then convert to list
            embeddings = cls.embedding_model.encode(
                texts,
                batch_size=32,  # Optimal batch size for multi-qa-mpnet-base-dot-v1
                show_progress_bar=False,
                normalize_embeddings=True,  # Better for cosine similarity
                convert_to_numpy=True  # Get numpy array first
            )
            
            # Convert numpy array to list
            embeddings = embeddings.tolist()
            
            embedding_time = time.time() - start_time
            logger.info(f"Generated {len(embeddings)} embeddings in {embedding_time:.2f}s ({len(embeddings)/embedding_time:.1f} chunks/sec)")

            # Add to ChromaDB in batches to avoid memory issues with large documents
            batch_size = 100
            total_added = 0
            
            for i in range(0, len(texts), batch_size):
                batch_end = min(i + batch_size, len(texts))
                batch_embeddings = embeddings[i:batch_end]
                batch_texts = texts[i:batch_end]
                batch_metadatas = metadatas[i:batch_end]
                batch_ids = ids[i:batch_end]
                
                cls.collection.add(
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                total_added += len(batch_texts)
                if len(texts) > batch_size:
                    logger.info(f"Added batch {i//batch_size + 1}: {total_added}/{len(texts)} chunks")

            total_time = time.time() - start_time
            logger.info(f"Successfully added {len(texts)} documents to ChromaDB in {total_time:.2f}s total")

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    @classmethod
    def _normalize_filter(cls, filter_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Normalize filter dictionary to ChromaDB's expected format.
        ChromaDB requires explicit $and operator when multiple conditions are present.

        Args:
            filter_dict: Dict with filter conditions like {"user_id": "...", "doc_id": "..."}

        Returns:
            Normalized filter dict with proper operators
        """
        if not filter_dict:
            return None

        # If only one condition, return as-is
        if len(filter_dict) == 1:
            return filter_dict

        # Multiple conditions - wrap in $and operator
        conditions = [
            {key: value} for key, value in filter_dict.items()
        ]

        return {"$and": conditions}

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

            # Normalize filter to ChromaDB's expected format
            normalized_filter = cls._normalize_filter(filter_dict)

            results = cls.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where=normalized_filter
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

            # Step 3: Advanced multi-signal hybrid scoring
            key_concepts = set(expansion.get('key_concepts', []))
            exclusion_terms = set(expansion.get('exclusion_terms', []))
            context_hints = [h.lower()
                             for h in expansion.get('context_hints', [])]
            query_type = expansion.get('query_type', 'general')
            hypothetical_answers = expansion.get('hypothetical_answers', [])

            scored_results = []
            for chunk_id, candidate in all_candidates.items():
                doc = candidate['document']
                metadata = candidate['metadata']
                distance = candidate['distance']

                # 1. Semantic similarity score (from embedding distance)
                semantic_score = 1.0 - min(distance, 1.0)

                # 2. Enhanced lexical matching with query + variants + hypotheticals
                all_variants = [query_text] + \
                    expansion.get('semantic_variants', [])[:4]
                lexical_scores = [calculate_lexical_score(
                    v, doc) for v in all_variants]
                keyword_score = max(lexical_scores) if lexical_scores else 0.0

                # 3. Hypothetical answer similarity (HyDE)
                hyde_score = 0.0
                if hypothetical_answers:
                    hyde_scores = [calculate_lexical_score(
                        hyp, doc) for hyp in hypothetical_answers[:2]]
                    hyde_score = max(hyde_scores) if hyde_scores else 0.0

                # 4. Key concept coverage with weighted importance
                doc_tokens = set(tokenize(doc))
                concept_matches = key_concepts.intersection(doc_tokens)
                # Weight by how early concepts appear in query (earlier = more important)
                concept_score = len(
                    concept_matches) / max(len(key_concepts), 1) if key_concepts else 0.0

                # 5. Exclusion term detection (critical for insurance queries)
                exclusion_matches = exclusion_terms.intersection(doc_tokens)
                exclusion_score = len(
                    exclusion_matches) / max(len(exclusion_terms), 1) if exclusion_terms else 0.0
                # Boost if query is about exclusions
                if query_type == 'exclusion' or 'not covered' in query_text.lower() or 'excluded' in query_text.lower():
                    exclusion_score *= 2.0

                # 6. Context hint matching (section titles, headers)
                context_score = 0.0
                if context_hints:
                    chunk_text_lower = doc.lower()
                    matching_hints = sum(
                        1 for hint in context_hints if hint in chunk_text_lower)
                    context_score = matching_hints / max(len(context_hints), 1)

                # 7. Multi-query match confidence
                multi_match_bonus = min(
                    len(candidate['query_matches']) * 0.05, 0.2)

                # 8. Document length penalty (very short chunks might be incomplete)
                # Normalize to 500 chars
                length_score = min(len(doc) / 500.0, 1.0)

                # 9. Metadata relevance (e.g., filename matching query terms)
                metadata_score = 0.0
                filename = metadata.get('filename', '').lower()
                if any(term in filename for term in tokenize(query_text)[:3]):
                    metadata_score = 0.5

                # Adaptive weighted combination based on query type
                if query_type == 'definition':
                    # For definitions, prioritize semantic + concept coverage
                    combined_score = (
                        0.40 * semantic_score +
                        0.25 * concept_score +
                        0.15 * keyword_score +
                        0.10 * hyde_score +
                        0.05 * context_score +
                        0.05 * multi_match_bonus
                    )
                elif query_type == 'exclusion':
                    # For exclusions, heavily weight exclusion terms
                    combined_score = (
                        0.30 * semantic_score +
                        0.30 * exclusion_score +
                        0.20 * keyword_score +
                        0.10 * context_score +
                        0.10 * multi_match_bonus
                    )
                elif query_type == 'coverage':
                    # For coverage, balance semantic + lexical + concepts
                    combined_score = (
                        0.35 * semantic_score +
                        0.25 * keyword_score +
                        0.15 * concept_score +
                        0.10 * hyde_score +
                        0.10 * context_score +
                        0.05 * multi_match_bonus
                    )
                else:
                    # General balanced scoring
                    combined_score = (
                        0.35 * semantic_score +
                        0.20 * keyword_score +
                        0.15 * concept_score +
                        0.10 * hyde_score +
                        0.08 * exclusion_score +
                        0.07 * context_score +
                        0.03 * length_score +
                        0.02 * metadata_score
                    )

                # Add multi-match bonus universally
                combined_score += multi_match_bonus * 0.1

                scored_results.append({
                    'score': min(combined_score, 1.0),
                    'document': doc,
                    'metadata': candidate['metadata'],
                    'id': chunk_id,
                    'distance': distance,
                    'debug': {
                        'semantic': round(semantic_score, 3),
                        'lexical': round(keyword_score, 3),
                        'hyde': round(hyde_score, 3),
                        'concepts': round(concept_score, 3),
                        'exclusions': round(exclusion_score, 3),
                        'context': round(context_score, 3),
                        'multi_match': round(multi_match_bonus, 3),
                        'length': round(length_score, 3),
                        'metadata': round(metadata_score, 3)
                    }
                })

            # Step 4: Sort and apply diversity-aware reranking
            scored_results.sort(key=lambda x: x['score'], reverse=True)

            # Ensure chunk diversity (avoid too many similar chunks from same document)
            diverse_results = []
            doc_chunk_count = {}
            max_per_doc = max(2, n_results // 3)  # Max 2-3 chunks per document

            for result in scored_results:
                doc_id = result['metadata'].get('doc_id', 'unknown')
                count = doc_chunk_count.get(doc_id, 0)

                if count < max_per_doc:
                    diverse_results.append(result)
                    doc_chunk_count[doc_id] = count + 1

                if len(diverse_results) >= n_results:
                    break

            # If diversity filtering was too aggressive, add more from top scores
            if len(diverse_results) < n_results:
                for result in scored_results:
                    if result not in diverse_results:
                        diverse_results.append(result)
                        if len(diverse_results) >= n_results:
                            break

            top_results = diverse_results[:n_results]

            reranked = {
                'documents': [[r['document'] for r in top_results]],
                'metadatas': [[r['metadata'] for r in top_results]],
                'ids': [[r['id'] for r in top_results]],
                'distances': [[r['distance'] for r in top_results]]
            }

            # Log detailed scoring breakdown for top result
            if top_results:
                top = top_results[0]
                logger.info(
                    f"Enhanced retrieval: {len(all_candidates)} candidates → {len(top_results)} diverse results\n"
                    f"Query type: {query_type} | Top score: {top['score']:.3f}\n"
                    f"Score breakdown: sem={top['debug']['semantic']:.3f}, "
                    f"lex={top['debug']['lexical']:.3f}, hyde={top['debug']['hyde']:.3f}, "
                    f"concept={top['debug']['concepts']:.3f}, excl={top['debug']['exclusions']:.3f}, "
                    f"ctx={top['debug']['context']:.3f}\n"
                    f"Concepts found: {len(key_concepts)}, Exclusion terms: {len(exclusion_terms)}, "
                    f"Context hints: {len(context_hints)}"
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
            # Query all documents for this user (single condition, no normalization needed)
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
