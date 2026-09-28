import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_agent_llm(temperature: float = 0.1):
    provider = (settings.LLM_PROVIDER or "ollama").lower()
    
    if provider == "openai" and settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL or "gpt-4o-mini",
            temperature=temperature,
            openai_api_key=settings.OPENAI_API_KEY
        )
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL or "gemini-1.5-flash",
            temperature=temperature,
            google_api_key=settings.GEMINI_API_KEY
        )
    elif provider == "ollama":
        try:
            from langchain_community.chat_models.ollama import ChatOllama
            return ChatOllama(
                model=settings.LLM_MODEL or "llama3",
                base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
                temperature=temperature
            )
        except Exception:
            pass
            
    # Fallback to OpenAI if key exists
    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=temperature,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
    return None
