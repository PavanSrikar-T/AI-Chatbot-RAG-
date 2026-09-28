from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False) # pdf, docx, txt, md
    content = Column(String, nullable=False)
    metadata_ = Column(JSON, nullable=True) # store additional extracted info
    status = Column(String, default="processing") # processing, completed, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    chunk_metadata = Column(JSON, nullable=True) # additional metadata specific to chunk
    
    document = relationship("Document", back_populates="chunks")
