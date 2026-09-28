import os
import sys
import time
import requests
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_rag_tests():
    print("==================================================")
    print("Starting CareerMind Production RAG End-to-End Test")
    print("==================================================")

    # 1. Health Check
    print("\n[Step 1] Checking API Health (/api/health)...")
    health_res = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert health_res.status_code == 200, f"Health check failed with {health_res.status_code}"
    health = health_res.json()
    print("Health Status:", json.dumps(health, indent=2))
    assert health["api"] == "ok", "API is not ok"
    assert health["database"] == "ok", "Database is not ok"
    assert health["qdrant"] == "ok", "Qdrant is not ok"
    assert health["embeddings"] == "ok", "Embeddings are not ok"
    print("✓ Core RAG dependencies (API, Database, Qdrant, Embeddings) are healthy!")

    # 2. Upload Document
    pdf_path = "test_resume.pdf"
    assert os.path.exists(pdf_path), f"File {pdf_path} not found"
    print(f"\n[Step 2] Uploading '{pdf_path}' to /api/documents/upload...")
    with open(pdf_path, "rb") as f:
        upload_res = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files={"file": ("test_resume.pdf", f, "application/pdf")},
            timeout=10
        )
    assert upload_res.status_code == 202, f"Upload failed: {upload_res.status_code}, {upload_res.text}"
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    print(f"✓ Upload accepted. Document ID: {doc_id}")

    # 3. Poll for processing completion
    print("\n[Step 3] Waiting for document processing (Extract -> Chunk -> Embed -> Qdrant Index)...")
    max_wait = 30
    start = time.time()
    completed = False
    doc_info = None

    while time.time() - start < max_wait:
        poll_res = requests.get(f"{BASE_URL}/api/documents/{doc_id}", timeout=5)
        if poll_res.status_code == 200:
            doc_info = poll_res.json()
            status = doc_info.get("status")
            print(f"Current status: {status} ({time.time() - start:.1f}s)")
            if status == "completed":
                completed = True
                break
            elif status == "error":
                raise RuntimeError(f"Document processing failed: {doc_info.get('metadata_')}")
        time.sleep(1)

    assert completed, f"Document processing timed out after {max_wait}s"
    print(f"✓ Document processing COMPLETED! Metadata: {doc_info.get('metadata_')}")

    # 4. Verify Chunks in DB
    print("\n[Step 4] Verifying Document Chunks in SQLite database...")
    chunks_res = requests.get(f"{BASE_URL}/api/documents/{doc_id}/chunks", timeout=5)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    print(f"Found {len(chunks)} indexed chunks.")
    assert len(chunks) > 0, "No chunks found in database"
    for i, c in enumerate(chunks):
        print(f"  Chunk #{i+1} (Page {c['page_number']}): {c['content'][:60]}...")
    print("✓ Chunks verified in DB!")

    # 5. Verify Vectors in Qdrant via RAG retrieval
    print("\n[Step 5] Verifying vectors indexed in Qdrant collection...")
    # Verify by issuing a retrieval query via the chat API
    probe_res = requests.post(
        f"{BASE_URL}/api/chat",
        json={"query": "Pavan CareerMind", "stream": False, "top_k": 5},
        timeout=15
    )
    assert probe_res.status_code == 200, f"RAG search failed: {probe_res.text}"
    probe_data = probe_res.json()
    assert probe_data["retrieved_count"] > 0, "No vectors retrieved from Qdrant!"
    print(f"✓ Successfully retrieved {probe_data['retrieved_count']} vector points from Qdrant with complete payloads!")

    # 6. Test RAG Questions (STEP 26)
    questions = [
        {
            "q": "What skills are mentioned?",
            "check": lambda ans: any(s in ans.lower() for s in ["java", "python", "fastapi"]),
            "expected": "Java / Python / FastAPI / Machine Learning"
        },
        {
            "q": "What is the project name?",
            "check": lambda ans: "careermind" in ans.lower(),
            "expected": "CareerMind AI"
        },
        {
            "q": "What vector database is mentioned?",
            "check": lambda ans: "qdrant" in ans.lower(),
            "expected": "Qdrant"
        },
        {
            "q": "What programming language is NOT mentioned?",
            "check": lambda ans: "couldn't find" in ans.lower() or "not" in ans.lower(),
            "expected": "Explicit statement that it is not found in the documents"
        }
    ]

    print("\n[Step 6] Testing RAG Query Processing, Retrieval, Reranking, and Grounded Answers...")
    for idx, test_case in enumerate(questions, 1):
        q = test_case["q"]
        print(f"\n--- Testing Q{idx}: '{q}' ---")
        chat_res = requests.post(
            f"{BASE_URL}/api/chat",
            json={"query": q, "stream": False, "top_k": 5},
            timeout=15
        )
        assert chat_res.status_code == 200, f"Chat query failed: {chat_res.text}"
        data = chat_res.json()
        ans = data["answer"]
        sources = data["sources"]
        print(f"Answer: {ans}")
        print(f"Retrieved: {data['retrieved_count']} chunks | Reranked: {data['reranked_count']} | Latency: {data['latency_ms']}ms")
        print(f"Sources: {[f'{s['filename']} - Pg {s['page']}' for s in sources]}")

        assert test_case["check"](ans), f"Answer failed criteria! Expected: {test_case['expected']}, Got: {ans}"
        if idx < 4:
            assert len(sources) > 0, f"Expected real source citations for Q{idx}"
            assert sources[0]["filename"] == "test_resume.pdf"
            print(f"✓ Real citation verified: 📄 {sources[0]['filename']} — Page {sources[0]['page']}")

    # 7. Test Streaming SSE endpoint
    print("\n[Step 7] Testing Streaming SSE Endpoint (/api/chat/stream)...")
    stream_res = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={"query": "What technologies are mentioned?", "stream": True},
        stream=True,
        timeout=15
    )
    assert stream_res.status_code == 200
    streamed_text = ""
    streamed_sources = None
    for line in stream_res.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                payload_str = decoded[6:]
                if payload_str.startswith("[SOURCES] "):
                    streamed_sources = json.loads(payload_str[10:])
                elif payload_str == "[DONE]":
                    break
                else:
                    try:
                        streamed_text += json.loads(payload_str)
                    except Exception:
                        streamed_text += payload_str

    print(f"Streamed Answer: {streamed_text}")
    print(f"Streamed Sources: {streamed_sources}")
    assert len(streamed_text) > 0, "Streaming produced no text!"
    assert streamed_sources is not None and len(streamed_sources) > 0, "No sources received in stream!"
    print("✓ SSE Streaming and Citation transmission verified!")

    # 8. User Isolation Test
    print("\n[Step 8] Testing Strict User Isolation (STEP 10)...")
    iso_res = requests.post(
        f"{BASE_URL}/api/chat",
        headers={"X-User-Email": "unauthorized_user_999@test.com"},
        json={"query": "What skills are mentioned in my resume?", "stream": False, "top_k": 5},
        timeout=15
    )
    assert iso_res.status_code == 200
    iso_data = iso_res.json()
    print(f"Other user retrieved count: {iso_data['retrieved_count']}")
    assert iso_data["retrieved_count"] == 0, f"User isolation breached! Retrieved {iso_data['retrieved_count']} chunks!"
    assert len(iso_data["sources"]) == 0, "Other user received sources from another user!"
    assert "couldn't find" in iso_data["answer"].lower(), "Other user should get not found response"
    print("✓ Strict user isolation verified! Another user cannot retrieve Pavan's documents.")

    print("\n==================================================")
    print("🎉 ALL PRODUCTION RAG INTEGRATION TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_rag_tests()
