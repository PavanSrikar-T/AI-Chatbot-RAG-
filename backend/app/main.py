import logging
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careermind")

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="CareerMind AI - Real Production RAG Copilot",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        logger.info("Initializing database models...")
        from app.core.db import engine
        from app.models.base import Base
        import app.models  # Import all models to register with Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Initializing Qdrant vector database...")
        from app.core.vector_db import init_vector_db
        init_vector_db()

        logger.info("Warming up reranker & embedding models...")
        try:
            from app.rag.reranker import reranker
            reranker.trigger_background_load()
            from app.rag.embedder import embedder
            embedder.embed_query("warmup")
        except Exception as e:
            logger.warning(f"Warmup warning: {e}")

        logger.info("CareerMind AI backend initialization complete.")

    from app.api import auth, chat, documents, resume, jobs, health, interview, conversations, modules, profile, retention
    
    app.include_router(health.router, prefix="/api/health", tags=["health"])
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
    app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
    app.include_router(conversations.router, prefix="/api/chats", tags=["chats"])
    app.include_router(modules.router, prefix="/api/modules", tags=["modules"])
    app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
    app.include_router(retention.router, prefix="/api/retention", tags=["retention"])

    return app

app = create_app()
