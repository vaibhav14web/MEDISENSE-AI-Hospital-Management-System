from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class LLMStatusResponse(BaseModel):
    is_active: bool
    provider: str
    model: str
    has_api_key: bool
    tools_available: List[str]
    knowledge_base_records: int


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None
    image_path: Optional[str] = None


class ChatMessageResponse(BaseModel):
    session_id: UUID
    sender_role: str = "assistant"
    response: str
    tool_executed: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    cited_sources: List[Dict[str, Any]] = []
    confidence: float = 0.95


class ChatMessageItem(BaseModel):
    id: UUID
    sender_role: str
    message_text: str
    tool_executed: Optional[str] = None
    cited_sources: List[Dict[str, Any]] = []
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: UUID
    session_title: str
    messages: List[ChatMessageItem]
