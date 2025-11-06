from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    top_k: Optional[int] = None
    doc_id: Optional[str] = None  # Filter to specific document


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    references: Optional[List[Dict[str, Any]]] = None


class ChatSession(BaseModel):
    id: str
    user_id: str
    title: str
    messages: List[ChatMessage] = []
    created_at: datetime
    updated_at: datetime
