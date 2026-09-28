import asyncio
import httpx
import json

async def test_live():
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {"x-user-email": "dev@local.host", "Content-Type": "application/json"}

        # Test 1: Candidate says 'i dont know'
        print("=== TEST 1: Candidate says 'i dont know' ===")
        req_body = {
            "session_id": "test-session-123",
            "role": "AI/ML Engineer",
            "difficulty": "Intermediate",
            "interview_type": "Technical Round",
            "question": "Can you describe a scenario where you had to troubleshoot and optimize a complex algorithm in a production environment, and how you approached the problem, considering the trade-offs between performance, scalability, and maintainability?",
            "answer": "i dont know",
            "question_index": 1,
            "total_questions": 5,
            "use_resume": False
        }
        res = await client.post("http://localhost:8000/api/interview/evaluate", headers=headers, json=req_body)
        assert res.status_code == 200, f"Evaluate failed: {res.text}"
        data = res.json()
        eval_data = data.get("evaluation", {})
        print("Score:", eval_data.get("score"))
        print("What was correct:", eval_data.get("what_was_correct"))
        print("Drawbacks / What was missing:", eval_data.get("what_was_missing"))
        print("How to improve:", eval_data.get("how_to_improve"))
        print("Ideal answer:", eval_data.get("ideal_answer")[:250], "...")
        assert eval_data.get("score") in (1, 2), f"Expected score 1 or 2, got {eval_data.get('score')}"
        assert "demonstrated" in (eval_data.get("what_was_correct") or "").lower() or eval_data.get("what_was_correct") is None or "no " in (eval_data.get("what_was_correct") or "").lower()
        print("--> TEST 1 PASSED!")

        # Test 2: Candidate gives partial technical answer
        print("\n=== TEST 2: Candidate gives partial technical answer ===")
        req_body["answer"] = "I used a hash map to cache repeated results to speed up queries."
        res2 = await client.post("http://localhost:8000/api/interview/evaluate", headers=headers, json=req_body)
        assert res2.status_code == 200, f"Evaluate failed: {res2.text}"
        eval_data2 = res2.json().get("evaluation", {})
        print("Score:", eval_data2.get("score"))
        print("What was correct:", eval_data2.get("what_was_correct"))
        print("Drawbacks / What was missing:", eval_data2.get("what_was_missing"))
        print("Ideal answer:", eval_data2.get("ideal_answer")[:250], "...")
        print("--> TEST 2 PASSED!")

if __name__ == "__main__":
    asyncio.run(test_live())
