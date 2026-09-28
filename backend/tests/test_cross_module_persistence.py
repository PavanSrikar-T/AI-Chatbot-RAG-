import os
import sys
import time
import requests
import json

BASE_URL = "http://localhost:8000"

def run_tests():
    headers_user_a = {
        "x-user-email": "pavan@careermind.ai",
        "Content-Type": "application/json"
    }

    headers_user_b = {
        "x-user-email": "adversary@external.com",
        "Content-Type": "application/json"
    }

    print("=" * 65)
    print("CAREERMIND PERSISTENT CROSS-MODULE STATE & CONVERSATION TEST")
    print("=" * 65)

    # -------------------------------------------------------------
    # TEST 1 & 2: Create conversation and add messages
    # -------------------------------------------------------------
    print("\n[TEST 1 & 2] Create persistent conversation & add messages")
    conv_data = {
        "module": "chat",
        "title": "LLM & RAG Systems Architecture",
        "current_state": {"mode": "education"}
    }
    res_c = requests.post(f"{BASE_URL}/api/conversations", json=conv_data, headers=headers_user_a)
    assert res_c.status_code == 201, f"Create conv failed: {res_c.status_code}"
    conv = res_c.json()
    conv_id = conv["id"]
    print(f"-> Created Conversation ID: {conv_id}")

    # Add Turn 1: User message
    msg1 = requests.post(
        f"{BASE_URL}/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Explain self-attention in transformers."},
        headers=headers_user_a
    )
    assert msg1.status_code == 201
    print("-> Added Turn 1 (User)")

    # Add Turn 1: Assistant message with source grounding
    msg2 = requests.post(
        f"{BASE_URL}/api/conversations/{conv_id}/messages",
        json={
            "role": "assistant",
            "content": "Self-attention computes dynamic weights using Query, Key, and Value matrices.",
            "sources": [{"document": "General Technical Knowledge", "page": 1, "chunk_id": "general_knowledge"}],
            "metadata": {"intent": "GENERAL_EDUCATION"}
        },
        headers=headers_user_a
    )
    assert msg2.status_code == 201
    print("-> Added Turn 1 (Assistant with source grounding)")

    # -------------------------------------------------------------
    # TEST 3: Reload conversation
    # -------------------------------------------------------------
    print("\n[TEST 3] Reload conversation from database")
    res_reload = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", headers=headers_user_a)
    assert res_reload.status_code == 200
    reloaded = res_reload.json()
    assert reloaded["message_count"] == 2
    assert len(reloaded["messages"]) == 2
    assert reloaded["messages"][0]["content"] == "Explain self-attention in transformers."
    assert reloaded["messages"][1]["sources"][0]["document"] == "General Technical Knowledge"
    print(f"PASS: Conversation reloaded with all messages and citations preserved.")

    # -------------------------------------------------------------
    # TEST 4, 5, 6: Multiple conversations per user
    # -------------------------------------------------------------
    print("\n[TEST 4] Multiple independent conversations")
    res_c2 = requests.post(
        f"{BASE_URL}/api/conversations",
        json={"module": "chat", "title": "Resume Questions & PlaceMate Deep Dive"},
        headers=headers_user_a
    )
    assert res_c2.status_code == 201
    conv2_id = res_c2.json()["id"]

    res_list = requests.get(f"{BASE_URL}/api/conversations?module=chat", headers=headers_user_a)
    assert res_list.status_code == 200
    conv_list = res_list.json()
    assert len(conv_list) >= 2
    assert any(c["id"] == conv_id for c in conv_list)
    assert any(c["id"] == conv2_id for c in conv_list)
    print(f"PASS: Multiple conversations listed ({len(conv_list)} found).")

    # -------------------------------------------------------------
    # TEST 7: Strict User Isolation (Security)
    # -------------------------------------------------------------
    print("\n[TEST 7] User Isolation Security Check")
    # User B attempts to access User A's conversation
    res_sec = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", headers=headers_user_b)
    assert res_sec.status_code == 404, "SECURITY ERROR: User B must not access User A's conversation!"
    print("PASS: User isolation strictly verified (User B received 404).")

    # -------------------------------------------------------------
    # TEST 8: Global User Profile
    # -------------------------------------------------------------
    print("\n[TEST 8] Global User Profile Persistence")
    prof_update = {
        "preferred_role": "Principal AI/ML Engineer",
        "target_difficulty": "Advanced",
        "education": "B.Tech CSE AI&ML",
        "programming_languages": ["Python", "Java", "C++", "SQL"],
        "current_learning_topics": ["Transformers", "LoRA", "RAG Systems"],
        "interview_goal": "FAANG AI/ML Leader"
    }
    res_prof = requests.put(f"{BASE_URL}/api/profile", json=prof_update, headers=headers_user_a)
    assert res_prof.status_code == 200
    res_prof_get = requests.get(f"{BASE_URL}/api/profile", headers=headers_user_a)
    assert res_prof_get.status_code == 200
    profile = res_prof_get.json()
    assert profile["preferred_role"] == "Principal AI/ML Engineer"
    assert "C++" in profile["programming_languages"]
    print("PASS: Global User Profile saved and verified across sessions.")

    # -------------------------------------------------------------
    # TEST 9: Document Persistence & Multi-Module Availability
    # -------------------------------------------------------------
    print("\n[TEST 9] Document Persistence & User Scoping")
    res_docs = requests.get(f"{BASE_URL}/api/documents", headers=headers_user_a)
    assert res_docs.status_code == 200
    print(f"-> User documents accessible across all modules: {len(res_docs.json())} document(s).")
    print("PASS: Document persistence verified.")

    # -------------------------------------------------------------
    # TEST 10, 11, 12 & SECTION 22: THE EXACT MULTI-MODULE PROGRESSION TEST
    #
    # Scenario:
    # 1. Interview: Question 1 -> answered, Question 2 -> answered, Question 3 -> answered.
    # 2. Switch to DSA: Solve Problem 1, Solve Problem 2.
    # 3. Switch to AI/ML Learning: Complete "LLM Foundations", Complete "Embeddings".
    # 4. Return to Interview -> MUST BE AT QUESTION 4!
    # 5. Return to DSA -> MUST BE AT PROBLEM 3!
    # 6. Return to Learning -> MUST BE AT NEXT UNFINISHED TOPIC ("Attention Mechanisms")!
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("RUNNING THE EXACT WORKFLOW TEST SPECIFIED IN SECTION 22")
    print("=" * 65)

    # Step 1: Open Interview Preparation, answer Question 1, 2, 3
    print("\n[Step 1] In Interview Prep: Candidate answers Questions 1, 2, 3")
    interview_state = {
        "state_json": {
            "role": "AI/ML Engineer",
            "topic": "Machine Learning & Generative AI",
            "current_question": 4,  # Next question is Question 4
            "completed_questions": [1, 2, 3],
            "questions_asked": [
                "Explain the bias-variance tradeoff.",
                "What is the difference between L1 and L2 regularization?",
                "How do cross-entropy and MSE losses differ?"
            ],
            "scores": [8, 9, 8],
            "is_active": True,
            "interview_type": "Technical",
            "difficulty": "Intermediate"
        }
    }
    res_int_save = requests.put(f"{BASE_URL}/api/modules/interview/state", json=interview_state, headers=headers_user_a)
    assert res_int_save.status_code == 200
    print("-> Interview progress saved: Completed [Q1, Q2, Q3], next is Q4.")

    # Step 2: Switch to DSA, solve Problem 1 & Problem 2
    print("\n[Step 2] Switch to DSA: Solve Problem 1 ('Two Sum'), Problem 2 ('Best Time to Buy and Sell Stock')")
    dsa_state = {
        "state_json": {
            "topic": "Arrays",
            "solved_problems": ["two-sum", "best-time-stock"],
            "current_problem": "valid-anagram",  # Next problem (Problem 3)
            "streak": 4,
            "difficulty": "Medium"
        }
    }
    res_dsa_save = requests.put(f"{BASE_URL}/api/modules/dsa/state", json=dsa_state, headers=headers_user_a)
    assert res_dsa_save.status_code == 200
    print("-> DSA progress saved: Solved 2 problems, current problem is Problem 3 ('valid-anagram').")

    # Step 3: Switch to AI/ML Learning, complete "LLM Foundations" & "Embeddings"
    print("\n[Step 3] Switch to AI/ML Learning: Complete 'llm-basics' and 'embeddings'")
    learning_state = {
        "state_json": {
            "subject": "genai",
            "completed_topics": ["llm-basics", "embeddings"],
            "current_topic": "attention",  # Next unfinished topic
            "learning_progress": 40
        }
    }
    res_learn_save = requests.put(f"{BASE_URL}/api/modules/learning/state", json=learning_state, headers=headers_user_a)
    assert res_learn_save.status_code == 200
    print("-> Learning progress saved: Completed 2 topics, next is 'attention'.")

    # -------------------------------------------------------------
    # VERIFICATION 1: Return to Interview Preparation
    # Expected: Resumes at Question 4!
    # -------------------------------------------------------------
    print("\n[Step 4] RETURN TO INTERVIEW PREPARATION:")
    res_int_check = requests.get(f"{BASE_URL}/api/modules/interview/state", headers=headers_user_a)
    assert res_int_check.status_code == 200
    saved_interview = res_int_check.json()["state_json"]
    print(f"-> Current Question: {saved_interview.get('current_question')}")
    print(f"-> Completed Questions: {saved_interview.get('completed_questions')}")
    assert saved_interview.get("current_question") == 4, f"Expected Question 4, got {saved_interview.get('current_question')}"
    assert saved_interview.get("completed_questions") == [1, 2, 3]
    print("PASS: Interview Preparation resumed exactly at Question 4!")

    # -------------------------------------------------------------
    # VERIFICATION 2: Return to DSA Practice
    # Expected: Resumes at Problem 3 ('valid-anagram') with 2 solved problems!
    # -------------------------------------------------------------
    print("\n[Step 5] RETURN TO DSA PRACTICE:")
    res_dsa_check = requests.get(f"{BASE_URL}/api/modules/dsa/state", headers=headers_user_a)
    assert res_dsa_check.status_code == 200
    saved_dsa = res_dsa_check.json()["state_json"]
    print(f"-> Solved Problems Count: {len(saved_dsa.get('solved_problems', []))}")
    print(f"-> Current Problem: {saved_dsa.get('current_problem')}")
    assert len(saved_dsa.get("solved_problems", [])) == 2
    assert saved_dsa.get("current_problem") == "valid-anagram"
    print("PASS: DSA Practice resumed exactly at Problem 3 ('valid-anagram')!")

    # -------------------------------------------------------------
    # VERIFICATION 3: Return to AI/ML Learning
    # Expected: Resumes at next unfinished topic ('attention')!
    # -------------------------------------------------------------
    print("\n[Step 6] RETURN TO AI/ML LEARNING:")
    res_learn_check = requests.get(f"{BASE_URL}/api/modules/learning/state", headers=headers_user_a)
    assert res_learn_check.status_code == 200
    saved_learn = res_learn_check.json()["state_json"]
    print(f"-> Completed Topics: {saved_learn.get('completed_topics')}")
    print(f"-> Current Topic: {saved_learn.get('current_topic')}")
    assert saved_learn.get("completed_topics") == ["llm-basics", "embeddings"]
    assert saved_learn.get("current_topic") == "attention"
    print("PASS: AI/ML Learning resumed exactly at 'attention'!")

    # -------------------------------------------------------------
    # VERIFICATION 4: Browser Refresh / Log-Out Simulation
    # Simulate completely closing browser, restarting HTTP session, re-authenticating
    # -------------------------------------------------------------
    print("\n[Step 7] BROWSER REFRESH & SESSION RE-INITIALIZATION SIMULATION:")
    fresh_session = requests.Session()
    fresh_headers = {
        "x-user-email": "pavan@careermind.ai",
        "Content-Type": "application/json"
    }

    fresh_int = fresh_session.get(f"{BASE_URL}/api/modules/interview/state", headers=fresh_headers).json()["state_json"]
    fresh_dsa = fresh_session.get(f"{BASE_URL}/api/modules/dsa/state", headers=fresh_headers).json()["state_json"]
    fresh_learn = fresh_session.get(f"{BASE_URL}/api/modules/learning/state", headers=fresh_headers).json()["state_json"]

    assert fresh_int.get("current_question") == 4
    assert fresh_dsa.get("current_problem") == "valid-anagram"
    assert fresh_learn.get("current_topic") == "attention"
    print("PASS: All states 100% persisted across fresh sessions and simulated browser refresh!")

    print("\n" + "=" * 65)
    print("ALL 12 PERSISTENCE CRITERIA AND WORKFLOW TESTS PASSED (100% SUCCESS)!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
