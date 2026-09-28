from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class DocumentChunkSchema(BaseModel):
    id: str
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

class DocumentBase(BaseModel):
    title: str
    filename: str
    file_type: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    status: str
    metadata_: Optional[Dict[str, Any]] = None

class DocumentInDBBase(DocumentBase):
    id: str
    user_id: int
    status: str
    metadata_: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class Document(DocumentInDBBase):
    chunks: List[DocumentChunkSchema] = []
