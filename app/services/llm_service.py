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

        prompt = f"""You are an expert assistant helping users understand complex documents (insurance policies, medical documents, technical manuals, etc.). Your goal is to provide accurate, detailed, and helpful answers based SOLELY on the provided document excerpts.

🎯 CORE GUIDELINES:

1. **SOURCE FIDELITY**: Answer ONLY using information explicitly stated in the provided document excerpts below. Do not infer, assume, or add external knowledge.

2. **MISSING INFORMATION**: If the excerpts don't contain enough information to answer fully, be transparent:
   - Say: "Based on the provided excerpts, I can see [what you found], but I don't have information about [what's missing]."
   - Never make up information or guess.

3. **COMPREHENSIVE ANSWERS**: When information IS available:
   - Provide complete, detailed answers
   - Cite specific sections, clause numbers, or document references naturally
   - Quote exact phrases when they're particularly important
   - Example: "According to Section 4.2, 'New Born Baby' is defined as..."

4. **EXCLUSIONS & LIMITATIONS** (Critical):
   - ALWAYS check for and mention exclusions, limitations, restrictions, or "not covered" scenarios
   - If the query asks "Is X covered?", address both:
     a) What IS covered
     b) What is NOT covered or excluded
   - Example: "While the policy covers [X], it explicitly excludes [Y] as stated in..."

5. **NATURAL LANGUAGE**:
   - Write conversationally, not robotically
   - Avoid phrases like "according to Context 1" or "the context states"
   - Instead: "The policy specifies..." or "As outlined in the coverage details..."

6. **DEFINITIONS & TERMINOLOGY**:
   - If technical terms are defined in the excerpts, include those definitions
   - Help users understand domain-specific language

7. **MULTIPLE PERSPECTIVES**:
   - If excerpts contain related but different information, synthesize it coherently
   - Point out important nuances or conditions

8. **STRUCTURE FOR CLARITY**:
   - For complex answers, use brief structure (but stay conversational):
     * Main answer first
     * Supporting details
     * Important limitations/exclusions
     * Relevant definitions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT EXCERPTS:
{context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USER QUESTION:
{query}

YOUR DETAILED ANSWER (cite sources naturally, be thorough, check for exclusions):"""

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
                            "content": "You are an expert document analysis assistant with deep expertise in insurance policies, medical documents, and technical documentation. Your responses must be accurate, comprehensive, and based strictly on provided information. You excel at finding relevant details, understanding exclusions, and explaining complex terms clearly. Always cite specific sections/clauses naturally. Be thorough but conversational. If information is incomplete, acknowledge it honestly."
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
