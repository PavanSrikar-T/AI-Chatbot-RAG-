import pytest
from app.rag.embedder import embedder
from app.rag.reranker import reranker
from app.agents.job_analyst import job_analyst

@pytest.mark.asyncio
async def test_embedder():
    texts = ["This is a test document.", "Another test chunk."]
    embeddings = embedder.embed_texts(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0

@pytest.mark.asyncio
async def test_reranker():
    query = "What is Python?"
    docs = [
        {"id": "1", "payload": {"content": "Python is a programming language."}},
        {"id": "2", "payload": {"content": "The weather is nice today."}}
    ]
    
    reranked = reranker.rerank(query, docs)
    assert len(reranked) == 2
    assert reranked[0]["id"] == "1" # Should rank higher

@pytest.mark.asyncio
async def test_job_analyst_agent(mocker):
    # Mocking LLM call for testing
    mocker.patch.object(job_analyst.llm, 'ainvoke', return_value=mocker.Mock(content="Mock Analysis"))
    
    analysis = await job_analyst.analyze_job("Need a senior Python engineer with FastAPI experience.")
    assert "Mock Analysis" in analysis
