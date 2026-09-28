import logging
from fastapi import APIRouter
from sqlalchemy import text
from app.core.db import engine
from app.core.vector_db import qdrant, COLLECTION_NAME
from app.rag.embedder import embedder
from app.rag.generator import generator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", summary="Comprehensive system health check")
@router.get("/", summary="Comprehensive system health check")
async def health_check():
    health = {
        "api": "ok",
        "database": "unknown",
        "qdrant": "unknown",
        "embeddings": "unknown",
        "llm": "unknown",
    }
    
    # 1. Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["database"] = "ok"
    except Exception as e:
        health["database"] = f"error: {str(e)}"

    # 2. Qdrant check
    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        health["qdrant"] = "ok"
    except Exception as e:
        health["qdrant"] = f"error: {str(e)}"

    # 3. Embeddings check
    try:
        dim = embedder.dimension
        if dim > 0:
            health["embeddings"] = "ok"
        else:
            health["embeddings"] = "error: invalid dimension"
    except Exception as e:
        health["embeddings"] = f"error: {str(e)}"

    # 4. LLM check
    try:
        is_healthy, msg = await generator.check_health()
        health["llm"] = "ok" if is_healthy else f"error: {msg}"
    except Exception as e:
        health["llm"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in health.values())
    return {
        "status": "ok" if all_ok else "degraded",
        **health
    }
