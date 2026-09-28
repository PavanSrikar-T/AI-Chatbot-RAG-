import asyncio
import time
import httpx
import json

BASE_URL = "http://localhost:8000"
HEADERS = {"x-user-email": "dev@local.host", "Content-Type": "application/json"}

async def measure_chat(client: httpx.AsyncClient, query: str, label: str):
    start = time.time()
    first_token_time = None
    token_count = 0
    full_text = ""
    
    req_body = {
        "query": query,
        "stream": True,
        "mode": "auto",
        "history": []
    }
    
    async with client.stream("POST", f"{BASE_URL}/api/chat/stream", headers=HEADERS, json=req_body, timeout=60.0) as res:
        async for line in res.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break
            if data_str.startswith("[INTENT]") or data_str.startswith("[SOURCES]"):
                continue
            try:
                token = json.loads(data_str)
                if token:
                    if first_token_time is None:
                        first_token_time = time.time() - start
                    token_count += 1
                    full_text += token
            except Exception:
                pass
                
    total_time = time.time() - start
    ttft = first_token_time if first_token_time is not None else total_time
    print(f"[{label}] TTFT: {ttft:.2f}s | Total: {total_time:.2f}s | Tokens: {token_count} | Query: '{query[:40]}'")
    return {"label": label, "ttft": ttft, "total": total_time, "tokens": token_count}

async def measure_interview_question(client: httpx.AsyncClient):
    start = time.time()
    req_body = {
        "role": "AI/ML Engineer",
        "difficulty": "Intermediate",
        "interview_type": "Technical Round",
        "use_resume": True
    }
    res = await client.post(f"{BASE_URL}/api/interview/start", headers=HEADERS, json=req_body, timeout=60.0)
    total_time = time.time() - start
    data = res.json()
    print(f"[Interview Start/Question] Total: {total_time:.2f}s | Question: '{data.get('question', '')[:50]}...'")
    return {"label": "Interview Start", "total": total_time}

async def measure_interview_eval(client: httpx.AsyncClient, answer: str, label: str):
    start = time.time()
    req_body = {
        "session_id": "perf-session-1",
        "role": "AI/ML Engineer",
        "difficulty": "Intermediate",
        "interview_type": "Technical Round",
        "question": "Can you describe a scenario where you had to troubleshoot and optimize a complex algorithm in a production environment, considering trade-offs?",
        "answer": answer,
        "question_index": 1,
        "total_questions": 5,
        "use_resume": False
    }
    res = await client.post(f"{BASE_URL}/api/interview/evaluate", headers=HEADERS, json=req_body, timeout=60.0)
    total_time = time.time() - start
    data = res.json()
    score = data.get("evaluation", {}).get("score")
    print(f"[{label}] Total: {total_time:.2f}s | Score: {score}")
    return {"label": label, "total": total_time, "score": score}

async def run_benchmark():
    print("==================================================")
    print("RUNNING CAREERMIND PERFORMANCE BENCHMARK")
    print("==================================================")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. General Education Chat (Polymorphism)
        g1 = await measure_chat(client, "What is polymorphism in Java?", "General Chat 1 (Polymorphism)")
        
        # 2. General Education / Coding Chat (Binary Search)
        g2 = await measure_chat(client, "Explain binary search with an example", "General Chat 2 (Binary Search)")
        
        # 3. RAG Chat (Projects in resume)
        r1 = await measure_chat(client, "What projects have I worked on in my resume?", "RAG Chat 1 (Projects)")
        
        # 4. RAG Chat (PlaceMate specific)
        r2 = await measure_chat(client, "Tell me about my PlaceMate project from my resume", "RAG Chat 2 (PlaceMate)")
        
        # 5. Interview Question Generation
        iq = await measure_interview_question(client)
        
        # 6. Interview Evaluation (Non-answer)
        e1 = await measure_interview_eval(client, "i dont know", "Interview Eval 1 (Non-answer)")
        
        # 7. Interview Evaluation (Partial answer)
        e2 = await measure_interview_eval(client, "I used a hash map to cache repeated computation and avoid nested loop overhead.", "Interview Eval 2 (Partial Answer)")
        
        print("\n==================================================")
        print("SUMMARY BASELINE METRICS:")
        print(f"General Chat Avg Total: {((g1['total'] + g2['total']) / 2):.2f}s (TTFT: {((g1['ttft'] + g2['ttft']) / 2):.2f}s)")
        print(f"RAG Chat Avg Total: {((r1['total'] + r2['total']) / 2):.2f}s (TTFT: {((r1['ttft'] + r2['ttft']) / 2):.2f}s)")
        print(f"Interview Question Gen: {iq['total']:.2f}s")
        print(f"Interview Eval Avg: {((e1['total'] + e2['total']) / 2):.2f}s")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
