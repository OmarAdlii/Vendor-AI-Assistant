from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    vendor_id: str = Field(..., description="Vendor ID for session tracking")
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_calls: Optional[List[Dict[str, Any]]] = None

class WebSocketMessage(BaseModel):
    type: str = Field(..., description="Message type: 'chat', 'ping', 'error'")
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None

class AgentState(BaseModel):
    vendor_id: str
    session_id: str
    message_count: int = 0
    last_activity: datetime = Field(default_factory=datetime.now)
    
class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    content: bytes
    
class KnowledgeBaseQuery(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.7