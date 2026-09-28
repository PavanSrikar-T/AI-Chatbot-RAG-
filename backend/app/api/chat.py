import json
import time
import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator, List, Optional, Dict, Any

from app.api.deps import get_current_active_user
from app.models.user import User
from app.rag.retriever import retriever, is_broad_query
from app.rag.reranker import reranker
from app.rag.generator import generator
from app.rag.intent import classify_intent, QueryIntent, KnowledgeMode

from app.core.perf import PerformanceTracker

logger = logging.getLogger(__name__)
DEBUG_RAG = os.getenv("DEBUG_RAG", "true").lower() in ["true", "1", "yes"]

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    stream: bool = True
    top_k: int = 5
    mode: Optional[str] = "auto"
    history: Optional[List[ChatMessage]] = None


class SourceItem(BaseModel):
    document: str
    filename: str
    page: int
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    retrieved_count: int
    reranked_count: int
    latency_ms: float
    intent: Optional[str] = None


def select_context_chunks(candidates: List[Dict[str, Any]], is_broad: bool, max_chunks: int = 6) -> List[Dict[str, Any]]:
    """Filters empty/declaration chunks, applies diversity coverage, and sorts in document reading order."""
    if not candidates:
        return []
    
    filtered = []
    for c in candidates:
        content = (c.get("content") or c.get("text") or "").strip()
        if not content:
            continue
        content_lower = content.lower()
        if "i hereby declare that all the information" in content_lower or "declaration" in content_lower:
            continue
        filtered.append(c)

    if not filtered:
        filtered = candidates

    target_count = max_chunks if is_broad else min(len(filtered), 4)
    selected = filtered[:target_count]

    def sort_key(doc):
        doc_id = str(doc.get("document_id") or "")
        chunk_idx = doc.get("chunk_index")
        if chunk_idx is None:
            chunk_idx = 0
        page = doc.get("page_number") or doc.get("page") or 1
        return (doc_id, int(chunk_idx), int(page))

    selected.sort(key=sort_key)
    return selected


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    tracker = PerformanceTracker("chat_stream")
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    history_dicts = [{"role": m.role, "content": m.content} for m in request.history] if request.history else []
    
    with tracker.measure("intent"):
        intent = classify_intent(query, history=history_dicts, mode=request.mode)

    context_docs = []
    sources = []
    retrieved_count = 0
    reranked_count = 0

    # -------------------------------------------------------------
    # PIPELINE 1: PURE GENERAL EDUCATION, CODING & CAREER GUIDANCE (0ms RAG)
    # Fast path: do not make user wait for unnecessary vector search/reranking
    # -------------------------------------------------------------
    has_resume_keywords = bool(re.search(r'\b(my|resume|cv|project|placemate|innovest|chemotherapy|hybrid ai|internship)\b', query, re.I))

    if intent in (QueryIntent.GENERAL_EDUCATION, QueryIntent.CODING_PROBLEM, QueryIntent.CAREER_GUIDANCE) and not has_resume_keywords:
        sources = [{
            "document": "General Technical Knowledge",
            "filename": "General Technical Knowledge",
            "page": 1,
            "chunk_id": "general_knowledge"
        }]

    # -------------------------------------------------------------
    # PIPELINE 2: DOCUMENT / RESUME GROUNDED RAG (Strict precision)
    # -------------------------------------------------------------
    elif intent == QueryIntent.DOCUMENT_QA:
        is_broad = is_broad_query(query)
        with tracker.measure("retrieval"):
            retrieved_docs = retriever.retrieve(
                query=query,
                user_id=current_user.id,
                top_k=10 if is_broad else 6,
                use_hybrid=True
            )
        retrieved_count = len(retrieved_docs)

        with tracker.measure("rerank"):
            rerank_budget = 5 if is_broad else 4
            reranked_docs = reranker.rerank(query, retrieved_docs, top_k=rerank_budget)
            context_docs = select_context_chunks(reranked_docs, is_broad=is_broad, max_chunks=4)
            reranked_count = len(context_docs)

        seen_sources = set()
        for doc in context_docs:
            payload = doc.get("payload") or doc
            filename = payload.get("filename") or doc.get("filename") or "Document"
            page = payload.get("page") or payload.get("page_number") or doc.get("page") or 1
            chunk_id = payload.get("chunk_id") or doc.get("chunk_id") or doc.get("id") or ""
            source_key = (filename, page)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "document": filename,
                    "filename": filename,
                    "page": int(page),
                    "chunk_id": str(chunk_id)
                })

    # -------------------------------------------------------------
    # PIPELINE 3: PERSONALIZED INTERVIEW / PROJECT MODE (RAG only if required)
    # -------------------------------------------------------------
    else:
        if intent == QueryIntent.PROJECT_INTERVIEW or has_resume_keywords:
            try:
                with tracker.measure("retrieval"):
                    retrieved_docs = retriever.retrieve(
                        query=query,
                        user_id=current_user.id,
                        top_k=6,
                        use_hybrid=True
                    )
                retrieved_count = len(retrieved_docs)
                if retrieved_docs:
                    with tracker.measure("rerank"):
                        reranked_docs = reranker.rerank(query, retrieved_docs, top_k=3)
                        context_docs = select_context_chunks(reranked_docs, is_broad=False, max_chunks=3)
                        reranked_count = len(context_docs)

                    seen_sources = set()
                    for doc in context_docs:
                        payload = doc.get("payload") or doc
                        filename = payload.get("filename") or doc.get("filename") or "Resume"
                        page = payload.get("page") or payload.get("page_number") or doc.get("page") or 1
                        chunk_id = payload.get("chunk_id") or doc.get("chunk_id") or doc.get("id") or ""
                        source_key = (filename, page)
                        if source_key not in seen_sources:
                            seen_sources.add(source_key)
                            sources.append({
                                "document": filename,
                                "filename": filename,
                                "page": int(page),
                                "chunk_id": str(chunk_id)
                            })
            except Exception as e:
                logger.warning(f"Optional resume retrieval for interview mode failed: {e}")

        sources.append({
            "document": "General Technical & Interview Knowledge",
            "filename": "General Technical & Interview Knowledge",
            "page": 1,
            "chunk_id": "general_interview_knowledge"
        })

    # -------------------------------------------------------------
    # STREAM GENERATION VIA SSE & AUTO DB SAVE
    # -------------------------------------------------------------
    async def sse_generator() -> AsyncGenerator[str, None]:
        yield f"data: [INTENT] {json.dumps(intent.value)}\n\n"

        first_token = True
        full_response = ""
        try:
            async for token in generator.stream_answer(
                query=query,
                contexts=context_docs,
                intent=intent,
                history=history_dicts,
            ):
                if first_token:
                    tracker.record_ttft()
                    first_token = False
                full_response += token
                yield f"data: {json.dumps(token)}\n\n"
        except Exception as e:
            logger.error(f"[LLM STREAM ERROR] {e}")
            err_msg = f"Error generating answer: {str(e)}"
            full_response += f"\n\n{err_msg}"
            yield f"data: {json.dumps(err_msg)}\n\n"
            
        tracker.finish({"intent": intent.value, "chunks": reranked_count})

        # Save to DB if conversation_id provided
        conv_id = request.conversation_id
        if conv_id and full_response:
            try:
                from app.core.db import async_session_maker
                from app.models.conversation import Conversation, Message
                from sqlalchemy.future import select
                import uuid

                async with async_session_maker() as db:
                    res = await db.execute(select(Conversation).filter(
                        Conversation.id == conv_id,
                        Conversation.user_id == current_user.id
                    ))
                    conv = res.scalars().first()
                    if not conv:
                        conv = Conversation(
                            id=conv_id,
                            user_id=current_user.id,
                            module="chat",
                            title=query.strip().split("\n")[0][:45] or "New Conversation"
                        )
                        db.add(conv)
                        await db.flush()

                    user_msg = Message(
                        id=str(uuid.uuid4()),
                        conversation_id=conv_id,
                        role="user",
                        content=query
                    )
                    db.add(user_msg)

                    assistant_msg = Message(
                        id=str(uuid.uuid4()),
                        conversation_id=conv_id,
                        role="assistant",
                        content=full_response,
                        sources=sources,
                        metadata_={"intent": intent.value}
                    )
                    db.add(assistant_msg)

                    if conv.title in ["New Conversation", "New Discussion", "Untitled Chat"]:
                        first_line = query.strip().split("\n")[0][:45]
                        if first_line:
                            conv.title = first_line

                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to persist chat message to database: {e}")

        # Send source citations event
        yield f"data: [SOURCES] {json.dumps(sources)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("", response_model=ChatResponse)
async def chat_sync(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Synchronous chat endpoint for programmatic evaluation and testing."""
    start_time = time.time()
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    history_dicts = [{"role": m.role, "content": m.content} for m in request.history] if request.history else []
    intent = classify_intent(query, history=history_dicts, mode=request.mode)

    context_docs = []
    sources = []
    retrieved_count = 0
    reranked_count = 0

    has_resume_keywords = bool(re.search(r'\b(my|resume|cv|project|placemate|innovest|chemotherapy|hybrid ai|internship)\b', query, re.I))

    if intent in (QueryIntent.GENERAL_EDUCATION, QueryIntent.CODING_PROBLEM, QueryIntent.CAREER_GUIDANCE) and not has_resume_keywords:
        sources = [SourceItem(
            document="General Technical Knowledge",
            filename="General Technical Knowledge",
            page=1,
            chunk_id="general_knowledge"
        )]
    elif intent == QueryIntent.DOCUMENT_QA:
        is_broad = is_broad_query(query)
        retrieved_docs = retriever.retrieve(query=query, user_id=current_user.id, top_k=10 if is_broad else 6)
        retrieved_count = len(retrieved_docs)
        rerank_budget = 5 if is_broad else 4
        reranked_docs = reranker.rerank(query, retrieved_docs, top_k=rerank_budget)
        context_docs = select_context_chunks(reranked_docs, is_broad=is_broad, max_chunks=4)
        reranked_count = len(context_docs)

        seen_sources = set()
        for doc in context_docs:
            payload = doc.get("payload") or doc
            filename = payload.get("filename") or doc.get("filename") or "Document"
            page = payload.get("page") or payload.get("page_number") or doc.get("page") or 1
            chunk_id = payload.get("chunk_id") or doc.get("chunk_id") or doc.get("id") or ""
            source_key = (filename, page)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(SourceItem(
                    document=filename,
                    filename=filename,
                    page=int(page),
                    chunk_id=str(chunk_id)
                ))
    else:
        # Personalized Interview mode (RAG only if resume context required)
        if intent == QueryIntent.PROJECT_INTERVIEW or has_resume_keywords:
            try:
                retrieved_docs = retriever.retrieve(query=query, user_id=current_user.id, top_k=6)
                retrieved_count = len(retrieved_docs)
                if retrieved_docs:
                    reranked_docs = reranker.rerank(query, retrieved_docs, top_k=3)
                    context_docs = select_context_chunks(reranked_docs, is_broad=False, max_chunks=3)
                    reranked_count = len(context_docs)

                    seen_sources = set()
                    for doc in context_docs:
                        payload = doc.get("payload") or doc
                        filename = payload.get("filename") or doc.get("filename") or "Resume"
                        page = payload.get("page") or payload.get("page_number") or doc.get("page") or 1
                        chunk_id = payload.get("chunk_id") or doc.get("chunk_id") or doc.get("id") or ""
                        source_key = (filename, page)
                        if source_key not in seen_sources:
                            seen_sources.add(source_key)
                            sources.append(SourceItem(
                                document=filename,
                                filename=filename,
                                page=int(page),
                                chunk_id=str(chunk_id)
                            ))
            except Exception as e:
                logger.warning(f"Optional retrieval in sync chat failed: {e}")

        sources.append(SourceItem(
            document="General Technical & Interview Knowledge",
            filename="General Technical & Interview Knowledge",
            page=1,
            chunk_id="general_interview_knowledge"
        ))

    tokens = []
    async for token in generator.stream_answer(
        query=query,
        contexts=context_docs,
        intent=intent,
        history=history_dicts,
    ):
        tokens.append(token)
    answer = "".join(tokens).strip()

    total_latency = (time.time() - start_time) * 1000
    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieved_count=retrieved_count,
        reranked_count=reranked_count,
        latency_ms=round(total_latency, 2),
        intent=intent.value,
    )


@router.post("/debug_pipeline")
async def chat_debug_pipeline(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Detailed pipeline inspection endpoint for debugging RAG steps."""
    from app.rag.embedder import embedder
    from app.rag.generator import build_prompt

    query = request.query.strip()
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history] if request.history else []
    intent = classify_intent(query, history=history_dicts, mode=request.mode)

    step1_query = query
    query_vector = embedder.embed_query(query)
    step2_embedding = {
        "dimension": len(query_vector),
        "sample_first_5": query_vector[:5] if query_vector else []
    }
    
    is_broad = is_broad_query(query)
    cand_top_k = 30 if is_broad else 20
    
    dense_results = retriever.dense_search(query, user_id=current_user.id, top_k=cand_top_k)
    step3_dense_count = len(dense_results)
    step4_dense = [
        {
            "chunk_id": d.get("chunk_id"),
            "filename": d.get("filename"),
            "page_number": d.get("page_number"),
            "similarity_score": round(float(d.get("score", 0.0)), 4),
            "content_excerpt": (d.get("content") or "")[:120].strip()
        }
        for d in dense_results
    ]
    
    sparse_results = retriever.sparse_search(query, user_id=current_user.id, top_k=cand_top_k)
    step5_bm25 = [
        {
            "chunk_id": d.get("chunk_id"),
            "filename": d.get("filename"),
            "page_number": d.get("page_number"),
            "score": round(float(d.get("score", 0.0)), 4),
            "content_excerpt": (d.get("content") or "")[:120].strip()
        }
        for d in sparse_results
    ]
    
    rrf_raw = retriever.reciprocal_rank_fusion(dense_results, sparse_results, top_k=cand_top_k)
    rrf_expanded = retriever.expand_adjacent_chunks(rrf_raw, user_id=current_user.id, query=query, is_broad=is_broad)
    step6_rrf = [
        {
            "chunk_id": d.get("chunk_id"),
            "filename": d.get("filename"),
            "page_number": d.get("page_number"),
            "rrf_score": round(float(d.get("rrf_score", 0.0)), 6),
            "content_excerpt": (d.get("content") or "")[:120].strip()
        }
        for d in rrf_expanded
    ]
    
    rerank_budget = 12 if is_broad else max(request.top_k, 6)
    reranked_docs = reranker.rerank(query, rrf_expanded, top_k=rerank_budget)
    step7_reranked = [
        {
            "chunk_id": d.get("chunk_id"),
            "filename": d.get("filename"),
            "page_number": d.get("page_number"),
            "rerank_score": round(float(d.get("rerank_score", 0.0)), 4) if "rerank_score" in d else None,
            "content_excerpt": (d.get("content") or "")[:120].strip()
        }
        for d in reranked_docs
    ]
    
    context_docs = select_context_chunks(reranked_docs, is_broad=is_broad, max_chunks=8)
    step8_final_chunks = [
        {
            "chunk_id": d.get("chunk_id"),
            "filename": d.get("filename"),
            "page_number": d.get("page_number"),
            "content": d.get("content")
        }
        for d in context_docs
    ]
    
    system_prompt, user_prompt = build_prompt(
        query=query,
        contexts=context_docs,
        intent=intent,
        history=history_dicts
    )
    step9_prompt = {
        "intent": intent.value,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    
    tokens = []
    async for token in generator.stream_answer(
        query=query,
        contexts=context_docs,
        intent=intent,
        history=history_dicts
    ):
        tokens.append(token)
    step10_answer = "".join(tokens).strip()
    
    return {
        "1_query": step1_query,
        "intent": intent.value,
        "2_query_embedding": step2_embedding,
        "3_dense_count": step3_dense_count,
        "4_dense_results": step4_dense,
        "5_bm25_results": step5_bm25,
        "6_rrf_results": step6_rrf,
        "7_reranker_results": step7_reranked,
        "8_final_chunks_to_llm": step8_final_chunks,
        "9_prompt": step9_prompt,
        "10_final_answer": step10_answer
    }
