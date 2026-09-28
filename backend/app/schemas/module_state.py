from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class ModuleStateUpdate(BaseModel):
    state_json: Dict[str, Any]

class ModuleStateResponse(BaseModel):
    module: str
    state_json: Dict[str, Any]
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
