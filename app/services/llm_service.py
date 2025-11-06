from typing import List, Dict, Any, AsyncGenerator
from groq import Groq, RateLimitError, APIError
import asyncio
from loguru import logger

from app.config import settings


class LLMService:

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.max_retries = 3
        self.retry_delay = 2
        logger.info(f"LLM Service initialized with model: {self.model}")

    def build_prompt(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        context_parts = []
        references = []

        for idx, chunk in enumerate(retrieved_chunks, start=1):
            text = chunk.get('text', '')
            doc_id = chunk.get('doc_id', 'unknown')
            chunk_id = chunk.get('chunk_id', 'unknown')

            # Use natural separators instead of "Context N"
            context_parts.append(f"{text}")
            references.append({
                'index': idx,
                'doc_id': doc_id,
                'chunk_id': chunk_id,
                'text_preview': text[:150] + '...' if len(text) > 150 else text
            })

        # Join with clear separators
        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are a knowledgeable assistant helping users understand their insurance documents. Answer questions clearly, naturally, and conversationally based on the provided information.

GUIDELINES:
1. Answer ONLY using information from the provided document excerpts below
2. If information is insufficient or missing, clearly state: "The provided documents don't contain information about [specific topic]"
3. Provide direct, clear answers without artificial structure
4. When referencing information, cite specific section numbers, clause names, or policy details mentioned in the documents
5. Be conversational and natural - avoid phrases like "according to Context 1" or "based on the context"
6. If you find relevant information, include the specific section/clause reference naturally (e.g., "According to Section 25..." or "As stated in the claim payment terms...")
7. **IMPORTANT**: Pay special attention to EXCLUSIONS, LIMITATIONS, and "NOT COVERED" sections - insurance questions often ask about what's excluded
8. If the query asks about coverage for something, check both what IS covered AND what is explicitly EXCLUDED

DOCUMENT EXCERPTS:
{context}

USER QUESTION:
{query}

ANSWER (Be direct and cite specific clauses):"""

        return prompt, references

    async def generate_streaming_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Starting streaming LLM response (attempt {attempt + 1})")

                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a knowledgeable document assistant. Provide clear, natural, conversational answers based on document content. Reference specific sections/clauses naturally without mentioning 'context' or numbered excerpts. If information is missing, say so directly."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

                logger.info("Streaming completed successfully")
                return

            except RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise Exception(
                        "Rate limit exceeded. Please try again later.")

            except APIError as e:
                logger.error(f"Groq API error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise Exception(f"LLM service error: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise Exception(f"Failed to generate response: {str(e)}")

    async def generate_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        prompt, references = self.build_prompt(query, retrieved_chunks)

        yield {
            'type': 'references',
            'content': references
        }

        async for token in self.generate_streaming_response(prompt):
            yield {
                'type': 'token',
                'content': token
            }


llm_service = LLMService()
