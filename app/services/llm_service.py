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

        prompt = f"""You are an expert document assistant. Provide accurate, CONCISE answers based ONLY on the document excerpts below.

🎯 ANSWER RULES:

1. **BREVITY**: Be direct and concise. Get to the point immediately. Avoid unnecessary elaboration.

2. **SOURCE ONLY**: Use ONLY information from the excerpts. Never add external knowledge or assumptions.

3. **MISSING INFO**: If info is incomplete, state briefly: "The excerpts show [X], but don't mention [Y]."

4. **COMPLETE BUT BRIEF**:
   - Answer the question fully but efficiently
   - Cite sections/clauses naturally (e.g., "Section 4.2 defines...")
   - Include key details, skip filler words

5. **EXCLUSIONS MATTER**:
   - Always mention limitations/exclusions when relevant
   - For "Is X covered?": State what IS and ISN'T covered briefly

6. **STRUCTURE** (for complex answers):
   • Direct answer first
   • Key details (bullet points if >3 items)
   • Important exclusions/conditions
   • Skip phrases like "according to the context" - just state facts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT EXCERPTS:
{context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USER QUESTION:
{query}

YOUR CONCISE ANSWER (direct, brief, complete - check exclusions):"""

        return prompt, references

    async def generate_streaming_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 600
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
                            "content": "You are an expert document assistant specializing in insurance, medical, and technical documents. Provide CONCISE, accurate answers using ONLY the provided excerpts. Be direct and efficient - answer fully but briefly. Cite sections naturally. Always mention exclusions/limitations when relevant. Use bullet points for multiple items. Skip filler words and unnecessary elaboration."
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
