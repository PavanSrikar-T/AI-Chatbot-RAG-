from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MessageCreate(BaseModel):
    role: str = "user"
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class ConversationCreate(BaseModel):
    module: str = "chat"
    title: Optional[str] = "New Conversation"
    is_pinned: Optional[bool] = False
    is_archived: Optional[bool] = False
    current_state: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    current_state: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

class ConversationResponse(BaseModel):
    id: str
    user_id: int
    module: str
    title: str
    summary: Optional[str] = None
    is_pinned: Optional[bool] = False
    is_archived: Optional[bool] = False
    current_state: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True
        populate_by_name = True
