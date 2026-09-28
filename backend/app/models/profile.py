from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    preferred_role = Column(String, nullable=True, default="AI/ML Engineer")
    target_difficulty = Column(String, nullable=True, default="Intermediate")
    education = Column(String, nullable=True)
    programming_languages = Column(JSON, nullable=True, default=lambda: ["Python", "Java", "SQL"])
    current_learning_topics = Column(JSON, nullable=True, default=lambda: ["LLMs", "RAG", "Transformers"])
    interview_goal = Column(String, nullable=True, default="Senior AI/ML Engineer")
    stats = Column(JSON, nullable=True, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="profile", uselist=False)
