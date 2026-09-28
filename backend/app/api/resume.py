from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.document import Document
from app.agents.resume_analyst import resume_analyst

router = APIRouter()

class ResumeAnalysisRequest(BaseModel):
    document_id: str

@router.post("/analyze")
async def analyze_resume(
    request: ResumeAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch document
    result = await db.execute(
        select(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # In a full app, we would retrieve all chunks for this doc and reconstruct text.
    # For now, we'll assume we have a way to fetch the full text or we analyze chunk by chunk.
    # Here we simulate fetching the raw content (which we should have stored or extracted).
    from app.models.document import DocumentChunk
    chunks_result = await db.execute(
        select(DocumentChunk).filter(DocumentChunk.document_id == request.document_id)
    )
    chunks = chunks_result.scalars().all()
    
    full_text = "\n".join([c.content for c in chunks])
    
    analysis_result = await resume_analyst.analyze_resume(full_text)
    
    return {"analysis": analysis_result}
