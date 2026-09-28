import asyncio
import os
import sys
import requests
import json

BASE_URL = "http://localhost:8000"

def test_persistence_api():
    headers = {
        "x-user-email": "dev@local.host",
        "Content-Type": "application/json"
    }

    print("==================================================")
    print("TESTING PERSISTENCE BACKEND API")
    print("==================================================")

    # 1. Health check
    res_health = requests.get(f"{BASE_URL}/api/health", headers=headers)
    assert res_health.status_code == 200, f"Health check failed: {res_health.status_code}"
    print("[1] Health check OK")

    # 2. Global Profile API
    res_profile = requests.get(f"{BASE_URL}/api/profile", headers=headers)
    assert res_profile.status_code == 200, f"Profile GET failed: {res_profile.status_code} {res_profile.text}"
    profile_data = res_profile.json()
    print(f"[2] Profile GET OK: preferred_role={profile_data.get('preferred_role')}")

    profile_update = {
        "preferred_role": "Generative AI & ML Engineer",
        "interview_goal": "Lead AI Architect",
        "stats": {"interviews_completed": 3, "problems_solved": 15}
    }
    res_prof_put = requests.put(f"{BASE_URL}/api/profile", json=profile_update, headers=headers)
    assert res_prof_put.status_code == 200
    updated_profile = res_prof_put.json()
    assert updated_profile.get("preferred_role") == "Generative AI & ML Engineer"
    print("[2] Profile PUT OK: Successfully updated and verified")

    # 3. Module State API: Interview Preparation Module
    interview_state = {
        "state_json": {
            "role": "AI/ML Engineer",
            "topic": "RAG",
            "current_question": 11,
            "completed_questions": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "weak_topics": ["reranking", "evaluation"],
            "difficulty": "Intermediate",
            "scores": [8, 7, 9, 8, 6, 9, 8, 7, 9, 8]
        }
    }
    res_mod_put = requests.put(f"{BASE_URL}/api/modules/interview/state", json=interview_state, headers=headers)
    assert res_mod_put.status_code == 200
    print("[3] Module State PUT for 'interview' OK")

    res_mod_get = requests.get(f"{BASE_URL}/api/modules/interview/state", headers=headers)
    assert res_mod_get.status_code == 200
    saved_mod = res_mod_get.json()
    assert saved_mod["state_json"]["current_question"] == 11
    assert len(saved_mod["state_json"]["completed_questions"]) == 10
    print("[3] Module State GET verified: resumed at Question 11!")

    # 4. Module State API: DSA Module
    dsa_state = {
        "state_json": {
            "topic": "Arrays & Two Pointers",
            "current_problem": "Two Sum II",
            "solved_problems": ["Two Sum", "Best Time to Buy and Sell Stock", "Contains Duplicate"],
            "difficulty": "Medium",
            "streak": 5
        }
    }
    requests.put(f"{BASE_URL}/api/modules/dsa/state", json=dsa_state, headers=headers)
    res_dsa_get = requests.get(f"{BASE_URL}/api/modules/dsa/state", headers=headers)
    assert res_dsa_get.status_code == 200
    assert len(res_dsa_get.json()["state_json"]["solved_problems"]) == 3
    print("[4] Module State for 'dsa' verified: 3 problems solved, current problem='Two Sum II'")

    # 5. Module State API: Learning Module
    learn_state = {
        "state_json": {
            "subject": "Generative AI",
            "current_topic": "Attention Mechanisms",
            "completed_topics": ["LLM Basics", "Tokenization", "Embeddings", "Transformers"],
            "topics_in_progress": ["Attention Mechanisms"],
            "learning_progress": 55
        }
    }
    requests.put(f"{BASE_URL}/api/modules/learning/state", json=learn_state, headers=headers)
    res_learn_get = requests.get(f"{BASE_URL}/api/modules/learning/state", headers=headers)
    assert res_learn_get.status_code == 200
    assert res_learn_get.json()["state_json"]["current_topic"] == "Attention Mechanisms"
    print("[5] Module State for 'learning' verified: current_topic='Attention Mechanisms'")

    # 6. Module State API: Verify switching between modules does NOT reset anything
    res_check_interview = requests.get(f"{BASE_URL}/api/modules/interview/state", headers=headers)
    assert res_check_interview.json()["state_json"]["current_question"] == 11
    print("[6] Cross-Module Switching Check: Interview module still on Question 11!")

    # 7. Persistent Conversations API
    new_conv = {
        "module": "chat",
        "title": "AI & RAG Architecture Discussion",
        "current_state": {"mode": "education"}
    }
    res_conv_post = requests.post(f"{BASE_URL}/api/conversations", json=new_conv, headers=headers)
    assert res_conv_post.status_code == 201
    conv_data = res_conv_post.json()
    conv_id = conv_data["id"]
    print(f"[7] Created Conversation: id={conv_id[:8]}... title='{conv_data['title']}'")

    # Add user message
    msg1 = {
        "role": "user",
        "content": "Explain the difference between RAG and fine-tuning."
    }
    res_msg1 = requests.post(f"{BASE_URL}/api/conversations/{conv_id}/messages", json=msg1, headers=headers)
    assert res_msg1.status_code == 201

    # Add assistant message with sources
    msg2 = {
        "role": "assistant",
        "content": "RAG connects an LLM to external documents via vector search, while fine-tuning updates neural weights.",
        "sources": [{"document": "General Technical Knowledge", "page": 1, "chunk_id": "general_knowledge"}]
    }
    res_msg2 = requests.post(f"{BASE_URL}/api/conversations/{conv_id}/messages", json=msg2, headers=headers)
    assert res_msg2.status_code == 201
    print("[7] Added user and assistant messages with source citations")

    # Retrieve full conversation
    res_conv_get = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", headers=headers)
    assert res_conv_get.status_code == 200
    retrieved_conv = res_conv_get.json()
    assert retrieved_conv["message_count"] == 2
    assert len(retrieved_conv["messages"]) == 2
    assert retrieved_conv["messages"][1]["sources"][0]["document"] == "General Technical Knowledge"
    print(f"[7] Retrieved Conversation verified: 2 messages stored persistently in DB")

    # List conversations
    res_list = requests.get(f"{BASE_URL}/api/conversations?module=chat", headers=headers)
    assert res_list.status_code == 200
    assert any(c["id"] == conv_id for c in res_list.json())
    print("[7] List Conversations OK: Found newly created conversation")

    # 8. User Isolation Check
    user_b_headers = {
        "x-user-email": "user_b@other.org",
        "Content-Type": "application/json"
    }
    # User B should NOT see User A's conversation
    res_user_b = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", headers=user_b_headers)
    assert res_user_b.status_code == 404, "Security violation: User B must not access User A's conversation"
    print("[8] User Isolation verified: User B received 404 for User A's conversation!")

    print("\n==================================================")
    print("ALL PERSISTENCE BACKEND API TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_persistence_api()
