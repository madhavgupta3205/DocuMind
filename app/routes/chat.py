from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
from datetime import datetime
from loguru import logger

from app.models.chat import QueryRequest, ChatSessionCreate
from app.services.vector_db import ChromaDB
from app.services.llm_service import llm_service
from app.services.database import ChatDB
from app.middleware.auth_middleware import get_current_user
from app.models.user import TokenData
from app.config import settings

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

limiter = Limiter(key_func=get_remote_address)


async def stream_sse_response(
    query: str,
    session_id: str = None,
    user_id: str = None,
    doc_id: str = None
):
    try:
        logger.info(f"Processing query for user {user_id}: {query[:100]}...")

        # Build filter dict - ALWAYS filter by user_id for privacy/security
        filter_dict = {"user_id": user_id}

        # Add document filter if specified (narrows down to specific doc)
        if doc_id:
            filter_dict["doc_id"] = doc_id
            logger.info(
                f"Filtering query to user {user_id}, document: {doc_id}")
        else:
            logger.info(f"Filtering query to user {user_id}'s documents only")

        # Debug: Log the exact filter being used
        logger.info(
            f"ChromaDB filter: {filter_dict} (user_id type: {type(user_id).__name__})")

        # Retrieve significantly more chunks with enhanced LLM-powered search
        # Cast a wider net for better recall, then aggressively rerank
        initial_retrieve = 50  # Retrieve many candidates
        top_k = min(settings.TOP_K_CHUNKS * 3, 20)  # Return more for context

        results = ChromaDB.search_with_reranking(
            query_text=query,
            n_results=top_k,
            retrieve_count=initial_retrieve,  # Cast very wide net
            use_llm_expansion=True,  # Enable LLM-powered query understanding
            filter_dict=filter_dict  # Apply document filter if specified
        )

        if not results['documents'][0]:
            yield f"data: {json.dumps({'type': 'token', 'content': 'No relevant documents found. Please upload documents first.'})}\n\n"
            return

        retrieved_chunks = []
        for i in range(len(results['documents'][0])):
            chunk = {
                'text': results['documents'][0][i],
                'doc_id': results['metadatas'][0][i].get('doc_id', 'unknown'),
                'chunk_id': results['metadatas'][0][i].get('chunk_id', 'unknown'),
                'distance': results['distances'][0][i] if 'distances' in results else 0.0,
                'filename': results['metadatas'][0][i].get('filename', 'unknown')
            }
            retrieved_chunks.append(chunk)

        # Use more chunks for better context (top 7-8 instead of 5)
        rerank_top_k = min(settings.RERANK_TOP_K + 2, len(retrieved_chunks))
        final_chunks = retrieved_chunks[:rerank_top_k]

        logger.info(f"Retrieved {len(final_chunks)} chunks for context")

        full_answer = ""
        references = []

        async for item in llm_service.generate_answer(query, final_chunks):
            if item['type'] == 'references':
                references = item['content']
                yield f"data: {json.dumps({'type': 'references', 'content': references})}\n\n"

            elif item['type'] == 'token':
                token = item['content']
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        if session_id and user_id:
            try:
                session = await ChatDB.get_session(session_id)
                if not session or session.get('user_id') != user_id:
                    logger.warning(
                        f"Invalid session {session_id} for user {user_id}")
                else:
                    user_message = {
                        'role': 'user',
                        'content': query,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    await ChatDB.add_message(session_id, user_message)

                    assistant_message = {
                        'role': 'assistant',
                        'content': full_answer,
                        'timestamp': datetime.utcnow().isoformat(),
                        'references': references
                    }
                    await ChatDB.add_message(session_id, assistant_message)

                    logger.info(f"Saved messages to session {session_id}")
            except Exception as e:
                logger.error(f"Failed to save chat history: {e}")

        yield f"data: {json.dumps({'type': 'done', 'content': 'complete'})}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_sse_response: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@router.post("/query")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def query_documents(
    request: Request,
    query_req: QueryRequest,
    current_user: TokenData = Depends(get_current_user)
):
    return StreamingResponse(
        stream_sse_response(
            query=query_req.query,
            session_id=query_req.session_id,
            user_id=current_user.user_id,
            doc_id=query_req.doc_id
        ),
        media_type="text/event-stream"
    )


@router.post("/sessions")
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: TokenData = Depends(get_current_user)
):
    session = await ChatDB.create_session(
        user_id=current_user.user_id,
        title=session_data.title
    )

    logger.info(f"Created chat session for user {current_user.email}")

    return {
        "id": session["_id"],
        "title": session["title"],
        "created_at": session["created_at"]
    }


@router.get("/sessions")
async def get_user_sessions(current_user: TokenData = Depends(get_current_user)):
    sessions = await ChatDB.get_user_sessions(current_user.user_id)

    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    session = await ChatDB.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    session = await ChatDB.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    success = await ChatDB.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")

    logger.info(f"Deleted session {session_id} for user {current_user.email}")

    return {"message": "Session deleted successfully"}
