from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserProfileUpdate(BaseModel):
    preferred_role: Optional[str] = None
    target_difficulty: Optional[str] = None
    education: Optional[str] = None
    programming_languages: Optional[List[str]] = None
    current_learning_topics: Optional[List[str]] = None
    interview_goal: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None

class UserProfileResponse(BaseModel):
    preferred_role: Optional[str] = "AI/ML Engineer"
    target_difficulty: Optional[str] = "Intermediate"
    education: Optional[str] = None
    programming_languages: Optional[List[str]] = ["Python", "Java", "SQL"]
    current_learning_topics: Optional[List[str]] = ["LLMs", "RAG", "Transformers"]
    interview_goal: Optional[str] = "Senior AI/ML Engineer"
    stats: Optional[Dict[str, Any]] = {}
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
