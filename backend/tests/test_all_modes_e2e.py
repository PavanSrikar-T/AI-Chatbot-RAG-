import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_modes():
    headers = {
        "x-user-email": "dev@local.host",
        "Content-Type": "application/json"
    }

    print("=" * 60)
    print("CAREERMIND MULTI-MODE E2E VALIDATION SUITE")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. DOCUMENT_QA MODE (Strict RAG + Real Citations)
    # -------------------------------------------------------------
    print("\n[TEST 1] DOCUMENT_QA: 'What projects have I worked on?'")
    payload1 = {
        "query": "What projects have I worked on?",
        "stream": False,
        "mode": "auto"
    }
    t0 = time.time()
    res1 = requests.post(f"{BASE_URL}/api/chat", json=payload1, headers=headers)
    lat1 = (time.time() - t0) * 1000
    assert res1.status_code == 200, f"Error {res1.status_code}: {res1.text}"
    data1 = res1.json()
    print(f"-> Intent: {data1.get('intent')}")
    print(f"-> Latency: {lat1:.1f}ms | Sources: {len(data1.get('sources', []))}")
    print(f"-> Answer snippet: {data1.get('answer', '')[:200]}...")
    assert data1.get("intent") == "DOCUMENT_QA", f"Expected DOCUMENT_QA, got {data1.get('intent')}"
    assert len(data1.get("sources", [])) > 0, "Expected document citations"
    assert "general_knowledge" not in [s.get("chunk_id") for s in data1.get("sources", [])]
    print("PASS: Mode 1 (Document QA) verified.")

    # -------------------------------------------------------------
    # 2. GENERAL_EDUCATION MODE (Pure General Technical Knowledge, NO RAG RESTRICTIONS)
    # -------------------------------------------------------------
    print("\n[TEST 2] GENERAL_EDUCATION: 'Explain polymorphism in Java'")
    payload2 = {
        "query": "Explain polymorphism in Java",
        "stream": False,
        "mode": "auto"
    }
    t0 = time.time()
    res2 = requests.post(f"{BASE_URL}/api/chat", json=payload2, headers=headers)
    lat2 = (time.time() - t0) * 1000
    assert res2.status_code == 200, f"Error {res2.status_code}: {res2.text}"
    data2 = res2.json()
    print(f"-> Intent: {data2.get('intent')}")
    print(f"-> Latency: {lat2:.1f}ms")
    print(f"-> Sources: {[s.get('document') for s in data2.get('sources', [])]}")
    print(f"-> Answer snippet: {data2.get('answer', '')[:200]}...")
    assert data2.get("intent") == "GENERAL_EDUCATION", f"Expected GENERAL_EDUCATION, got {data2.get('intent')}"
    assert "couldn't find this information in the uploaded documents" not in data2.get("answer", "").lower(), "Model must not falsely reject general technical questions"
    assert any("General Technical Knowledge" in s.get("document", "") for s in data2.get("sources", [])), "Source must indicate General Technical Knowledge"
    print("PASS: Mode 2 (General Education) verified.")

    # -------------------------------------------------------------
    # 3. PERSONALIZED INTERVIEW MODE (Resume Seed + General Knowledge)
    # -------------------------------------------------------------
    print("\n[TEST 3] INTERVIEW_PREPARATION: 'Train me for an AI/ML interview'")
    payload3 = {
        "query": "Train me for an AI/ML interview",
        "stream": False,
        "mode": "auto"
    }
    t0 = time.time()
    res3 = requests.post(f"{BASE_URL}/api/chat", json=payload3, headers=headers)
    lat3 = (time.time() - t0) * 1000
    assert res3.status_code == 200, f"Error {res3.status_code}: {res3.text}"
    data3 = res3.json()
    print(f"-> Intent: {data3.get('intent')}")
    print(f"-> Latency: {lat3:.1f}ms")
    print(f"-> Sources: {[s.get('document') for s in data3.get('sources', [])]}")
    print(f"-> Answer snippet: {data3.get('answer', '')[:200]}...")
    assert data3.get("intent") in ["INTERVIEW_PREPARATION", "PROJECT_INTERVIEW"], f"Expected interview intent, got {data3.get('intent')}"
    print("PASS: Mode 3 (Personalized Interview Preparation) verified.")

    # -------------------------------------------------------------
    # 4. PROJECT INTERVIEW MODE ('What questions can an interviewer ask about PlaceMate?')
    # -------------------------------------------------------------
    print("\n[TEST 4] PROJECT_INTERVIEW: 'What questions can an interviewer ask about PlaceMate?'")
    payload4 = {
        "query": "What questions can an interviewer ask about PlaceMate?",
        "stream": False,
        "mode": "auto"
    }
    res4 = requests.post(f"{BASE_URL}/api/chat", json=payload4, headers=headers)
    assert res4.status_code == 200
    data4 = res4.json()
    print(f"-> Intent: {data4.get('intent')}")
    print(f"-> Answer snippet: {data4.get('answer', '')[:200]}...")
    assert data4.get("intent") in ["PROJECT_INTERVIEW", "INTERVIEW_PREPARATION"]
    print("PASS: Mode 4 (Project Defense Interview) verified.")

    # -------------------------------------------------------------
    # 5. CODING PROBLEM MODE ('Give me a Java array problem')
    # -------------------------------------------------------------
    print("\n[TEST 5] CODING_PROBLEM: 'Give me a Java array problem'")
    payload5 = {
        "query": "Give me a Java array problem",
        "stream": False,
        "mode": "auto"
    }
    res5 = requests.post(f"{BASE_URL}/api/chat", json=payload5, headers=headers)
    assert res5.status_code == 200
    data5 = res5.json()
    print(f"-> Intent: {data5.get('intent')}")
    print(f"-> Answer snippet: {data5.get('answer', '')[:200]}...")
    assert data5.get("intent") == "CODING_PROBLEM"
    print("PASS: Mode 5 (Coding Problem) verified.")

    # -------------------------------------------------------------
    # 6. CONVERSATIONAL CONTINUITY (Turn 1: Polymorphism, Turn 2: Encapsulation)
    # -------------------------------------------------------------
    print("\n[TEST 6] CONVERSATIONAL CONTEXT: Follow-up 'Encapsulation' with history")
    payload6 = {
        "query": "Encapsulation",
        "stream": False,
        "mode": "auto",
        "history": [
            {"role": "user", "content": "Explain polymorphism in Java"},
            {"role": "assistant", "content": "Polymorphism allows objects to take many forms..."}
        ]
    }
    res6 = requests.post(f"{BASE_URL}/api/chat", json=payload6, headers=headers)
    assert res6.status_code == 200
    data6 = res6.json()
    print(f"-> Intent: {data6.get('intent')}")
    print(f"-> Answer snippet: {data6.get('answer', '')[:200]}...")
    assert data6.get("intent") == "GENERAL_EDUCATION"
    assert "couldn't find this information in the uploaded documents" not in data6.get("answer", "").lower()
    print("PASS: Conversational Multi-Turn Context verified.")

    # -------------------------------------------------------------
    # 7. MOCK INTERVIEW API (/api/interview/start & /evaluate)
    # -------------------------------------------------------------
    print("\n[TEST 7] MOCK INTERVIEW API: /api/interview/start and /evaluate")
    start_payload = {
        "role": "AI/ML Engineer",
        "difficulty": "Intermediate",
        "interview_type": "Technical",
        "use_resume": True
    }
    res_start = requests.post(f"{BASE_URL}/api/interview/start", json=start_payload, headers=headers)
    assert res_start.status_code == 200
    session_data = res_start.json()
    session_id = session_data.get("session_id")
    question_1 = session_data.get("question")
    print(f"-> Started Session {session_id[:8]}...")
    print(f"-> Question 1: {question_1}")
    assert question_1, "Expected Question 1 text"

    eval_payload = {
        "session_id": session_id,
        "role": "AI/ML Engineer",
        "difficulty": "Intermediate",
        "interview_type": "Technical",
        "question": question_1,
        "answer": "The bias-variance tradeoff balances underfitting and overfitting. High bias occurs when the model is too simple, while high variance occurs when the model captures noise. L1 regularization (Lasso) encourages sparsity by adding absolute weights to the loss, whereas L2 (Ridge) shrinks weights towards zero proportionally.",
        "question_index": 1,
        "total_questions": 5,
        "use_resume": True
    }
    res_eval = requests.post(f"{BASE_URL}/api/interview/evaluate", json=eval_payload, headers=headers)
    assert res_eval.status_code == 200
    eval_res = res_eval.json()
    evaluation = eval_res.get("evaluation", {})
    score = evaluation.get("score")
    print(f"-> Evaluation Score: {score}/10")
    print(f"-> Correct: {evaluation.get('what_was_correct', '')[:100]}...")
    print(f"-> Missing: {evaluation.get('what_was_missing', '')[:100]}...")
    print(f"-> Ideal Answer: {evaluation.get('ideal_answer', '')[:100]}...")
    print(f"-> Next Question: {eval_res.get('next_question')}")
    assert score is not None and score >= 1, "Evaluation score must be returned"
    print("PASS: Mock Interview API verified.")

    # -------------------------------------------------------------
    # 8. TOPIC QUESTION SET API (/api/interview/questions)
    # -------------------------------------------------------------
    print("\n[TEST 8] TOPIC QUESTION SET: Java Intermediate")
    qset_payload = {
        "topic": "Java",
        "difficulty": "Intermediate",
        "count": 5
    }
    res_qset = requests.post(f"{BASE_URL}/api/interview/questions", json=qset_payload, headers=headers)
    assert res_qset.status_code == 200
    qset_data = res_qset.json()
    questions = qset_data.get("questions", [])
    print(f"-> Returned {len(questions)} questions for Java")
    assert len(questions) >= 3, "Expected at least 3 curated questions"
    print("PASS: Topic Question Set API verified.")

    print("\n" + "=" * 60)
    print("ALL 8 E2E MULTI-MODE TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    test_modes()
