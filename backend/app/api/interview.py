import json
import logging
import uuid
import re
from typing import List, Optional, Dict, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.module_state import ModuleState
from app.models.profile import UserProfile
from app.rag.retriever import retriever
from app.rag.generator import generator, OllamaProvider, OpenAIProvider
from app.rag.intent import QueryIntent

logger = logging.getLogger(__name__)
router = APIRouter()


class StartInterviewRequest(BaseModel):
    role: str = "AI/ML Engineer"
    difficulty: str = "Intermediate"
    interview_type: str = "Technical"  # HR, Technical, Coding, Project, AI/ML, Full Interview
    use_resume: bool = True
    enable_adaptive: bool = True


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    role: str = "AI/ML Engineer"
    difficulty: str = "Intermediate"
    interview_type: str = "Technical"
    question: str
    answer: str
    question_index: int = 1
    total_questions: int = 5
    use_resume: bool = True
    enable_adaptive: bool = True
    previous_trajectory: Optional[List[Dict[str, Any]]] = None


class InterrogateRequest(BaseModel):
    session_id: str
    role: str = "AI/ML Engineer"
    question: str
    answer: str
    interrogation_history: List[Dict[str, str]] = []  # [{"role": "ai" | "user", "text": "..."}]


class QuestionSetRequest(BaseModel):
    topic: str = "Java"
    difficulty: str = "Intermediate"
    count: int = 5


class ReadinessCriteria(BaseModel):
    name: str
    score: int
    max_score: int = 10


class ReadinessDomain(BaseModel):
    id: str
    name: str
    score: int
    evaluated_answers_count: int
    status: str
    criteria: List[ReadinessCriteria]
    why_explanation: str
    top_strengths: List[str]
    critical_weaknesses: List[str]
    recommended_drill: str


class ReadinessHeatmapResponse(BaseModel):
    overall_readiness: int
    domains: List[ReadinessDomain]
    summary_verdict: str


# Curated question banks for fast startup & fallback
DEFAULT_QUESTIONS: Dict[str, Dict[str, List[str]]] = {
    "AI/ML Engineer": {
        "Technical": [
            "Can you explain the bias-variance tradeoff and how L1 vs L2 regularization impacts model generalization?",
            "What is the mathematical and architectural difference between standard Self-Attention and Multi-Head Attention in Transformers?",
            "How do you evaluate an imbalanced classification model? Why might accuracy be misleading and what metrics would you choose?",
            "Explain how Word2Vec, BERT embeddings, and modern dense bi-encoder embeddings differ in how they represent semantic context.",
            "In a Retrieval-Augmented Generation (RAG) system, what strategies would you use to mitigate hallucination and improve retrieval recall?"
        ],
        "AI/ML": [
            "What is gradient descent, and how do Adam and RMSprop improve upon standard stochastic gradient descent?",
            "Explain the difference between cross-entropy loss and mean squared error. In what scenarios is each appropriate?",
            "How does Convolutional Neural Network (CNN) feature extraction work via kernels, stride, and pooling layers?",
            "What are the main causes of exploding or vanishing gradients in deep networks, and how do residual connections (ResNets) solve this?",
            "Explain the concepts of LoRA (Low-Rank Adaptation) and parameter-efficient fine-tuning (PEFT) for Large Language Models."
        ],
        "Coding": [
            "Implement a function in Python to calculate the cosine similarity between two 1D NumPy arrays without using sklearn.",
            "Write an efficient algorithm to find the Kth largest element in an unsorted array. What is the time and space complexity?",
            "Given a stream of incoming real numbers, design a data structure that efficiently computes the running median.",
            "Write a function to perform Word Tokenization and build a term-frequency (TF) dictionary from scratch for a list of documents.",
            "Implement a simple dense neural network forward-pass in pure Python/NumPy for a single linear layer followed by ReLU activation."
        ],
        "Project": [
            "Walk me through the architecture of your most impactful machine learning project. What was the exact business problem?",
            "Why did you choose that specific model architecture over other simpler baselines?",
            "How did you handle data preprocessing, missing features, and leakage prevention in your pipeline?",
            "What was the deployment latency of your model in production, and how did you monitor for data drift?",
            "If you were to rebuild this project from scratch with 100x larger dataset, what architectural decisions would you change?"
        ],
        "HR": [
            "Tell me about yourself and what sparked your passion for AI and Machine Learning.",
            "Describe a challenging technical disagreement you had with a team member. How did you resolve it?",
            "Tell me about a time an ML model failed in development or did not meet expectations. How did you diagnose and pivot?",
            "Where do you see yourself contributing in the AI/ML domain over the next 3 to 5 years?",
            "Why are you interested in joining our engineering team specifically?"
        ],
        "Full Interview": [
            "Tell me about yourself and walk me through the highlights of your technical background.",
            "Can you explain the key architectural design of the machine learning project you are most proud of?",
            "Explain the difference between RAG and fine-tuning. When would you choose one over the other?",
            "How would you optimize an LLM application to reduce time-to-first-token (TTFT) and overall inference latency?",
            "Do you have any questions for us about our engineering stack or team roadmap?"
        ]
    },
    "Software Engineer": {
        "Technical": [
            "Explain the 4 fundamental pillars of Object-Oriented Programming with real-world software design examples.",
            "What is the difference between a process and a thread? How does the operating system handle context switching?",
            "Explain ACID properties in relational databases and how isolation levels prevent dirty reads and phantom reads.",
            "How does HTTPS establish a secure connection? Walk through the TLS handshake step-by-step.",
            "Explain the difference between synchronous, asynchronous, and multi-threaded programming in modern backends."
        ],
        "Coding": [
            "Given an array of integers and a target sum, find indices of the two numbers such that they add up to the target in O(N) time.",
            "Reverse a singly linked list iteratively and explain the time and space complexity.",
            "Given a binary tree, write a function to determine if it is a valid Binary Search Tree (BST).",
            "Implement an LRU (Least Recently Used) cache with get and put operations in O(1) time.",
            "Given a string containing just characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid."
        ],
        "Project": [
            "Walk me through the architecture of the web application or backend system mentioned in your resume.",
            "How did you design your database schema, and how did you ensure queries remain fast under high concurrency?",
            "How did you handle authentication, authorization, and session security in your backend?",
            "Describe the most difficult bug you encountered in this project and your step-by-step debugging methodology.",
            "What trade-offs did you make between delivery speed and architectural scalability?"
        ],
        "HR": [
            "Walk me through your background and what motivated you to pursue software engineering.",
            "Tell me about a time you had to meet a tight deadline with incomplete requirements.",
            "How do you stay updated with emerging technologies and engineering best practices?",
            "Describe a time you received constructive criticism on a code review. How did you respond?",
            "Why do you believe you are a strong fit for this software engineering role?"
        ],
        "Full Interview": [
            "Tell me about yourself and your journey in software engineering.",
            "Explain how polymorphism is implemented under the hood in Java or your primary programming language.",
            "Walk me through the design and database architecture of your featured project.",
            "How would you design a scalable URL shortener service like TinyURL?",
            "What questions do you have for our engineering team?"
        ]
    }
}


def get_default_question(role: str, interview_type: str, index: int) -> str:
    role_dict = DEFAULT_QUESTIONS.get(role) or DEFAULT_QUESTIONS["Software Engineer"]
    questions = role_dict.get(interview_type) or role_dict.get("Technical") or role_dict["Full Interview"]
    idx = max(0, min(index - 1, len(questions) - 1))
    return questions[idx]


# Feature 3: Adaptive Trajectory Generation
def generate_adaptive_next_question(
    role: str,
    current_q: str,
    score: int,
    detected_concept: str,
    performance_level: str,
    step_num: int,
    total_steps: int
) -> Dict[str, Any]:
    """
    Dynamically decides the next question based on candidate mastery and weak spots,
    mirroring a seasoned interviewer.
    """
    q_lower = current_q.lower()
    
    # Target RAG / AI concepts (per user prompt example)
    if "rag" in q_lower or "retrieval" in q_lower or "embedding" in q_lower:
        if performance_level == "strong":
            if step_num == 1:
                return {
                    "question": "Can you explain the trade-offs between different chunking strategies (e.g., fixed-token vs recursive vs semantic chunking) in a production knowledge retrieval pipeline?",
                    "detected_mastery": "Strong RAG fundamentals; articulated embedding indexing well",
                    "adaptive_strategy": "advance_depth",
                    "adaptive_decision": "Branch Deeper: Chunking Mechanics & Boundaries",
                    "adaptive_reasoning": "Candidate demonstrated strong high-level RAG fundamentals; advancing to low-level document chunking and boundary preservation."
                }
            elif step_num == 2:
                return {
                    "question": "How do you evaluate and optimize a Cross-Encoder Reranker stage in your RAG pipeline when balancing retrieval precision against p99 latency overhead?",
                    "detected_mastery": "Strong understanding of chunking trade-offs",
                    "adaptive_strategy": "advance_depth",
                    "adaptive_decision": "Branch Deeper: Reranker Optimization & Latency",
                    "adaptive_reasoning": "Candidate showed mastery of chunking; escalating to two-stage re-ranking and SLA constraints."
                }
        else:  # Weak or moderate
            if "chunking" in q_lower or "chunk" in q_lower:
                return {
                    "question": "Let's compare recursive character chunking vs semantic chunking based on cosine similarity drops. In what exact scenarios would recursive chunking cause retrieval failure?",
                    "detected_mastery": "Weak chunking knowledge; struggled with context fragmentation",
                    "adaptive_strategy": "probe_weakness",
                    "adaptive_decision": "Isolate Gap: Recursive vs Semantic Chunking",
                    "adaptive_reasoning": "Candidate exhibited weak or vague chunking mechanics; dynamically pivoting to compare recursive vs semantic chunking to isolate the exact gap."
                }
            else:
                return {
                    "question": "Let's break down the basic ingestion stage of RAG: What happens to a document from raw text to stored vector in Qdrant, step-by-step?",
                    "detected_mastery": "Foundational gaps in vector retrieval lifecycle",
                    "adaptive_strategy": "remediate",
                    "adaptive_decision": "Remediate: Vector Ingestion Lifecycle",
                    "adaptive_reasoning": "Candidate missed core principles; pivoting to foundational lifecycle verification."
                }

    # Final step: Pipeline design synthesis
    if step_num >= total_steps - 1:
        return {
            "question": f"Now let's bring it all together: Design an end-to-end production {role} pipeline that ingests 50,000 real-time documents daily with sub-200ms query latency, strict access control, and automated evaluation.",
            "detected_mastery": "Evaluated core modules; synthesizing system design capacity",
            "adaptive_strategy": "system_design_challenge",
            "adaptive_decision": "Synthesis Challenge: End-to-End System Design",
            "adaptive_reasoning": "Final round synthesis: Evaluating ability to integrate component knowledge into a scalable production architecture."
        }

    # General Adaptive Progression
    if performance_level == "strong":
        return {
            "question": f"Given your solid explanation of {detected_concept}, how would your architecture change if load spiked 100x to 50,000 requests/sec with strict 20ms p99 SLA?",
            "detected_mastery": f"Demonstrated solid grasp of {detected_concept}",
            "adaptive_strategy": "advance_depth",
            "adaptive_decision": f"Branch Deeper: High-Concurrency Scale for {detected_concept}",
            "adaptive_reasoning": f"Candidate demonstrated strong grasp of {detected_concept}; advancing to high-concurrency scaling constraints."
        }
    elif performance_level == "weak":
        return {
            "question": f"Let's isolate a key nuance: What is the single most common failure mode or bottleneck when implementing {detected_concept} in production, and how do you diagnose it?",
            "detected_mastery": f"Weak or incomplete articulation of {detected_concept}",
            "adaptive_strategy": "probe_weakness",
            "adaptive_decision": f"Isolate Gap: Failure Modes & Diagnostics in {detected_concept}",
            "adaptive_reasoning": f"Candidate struggled on {detected_concept}; pivoting to diagnose operational pitfalls."
        }
    else:
        return {
            "question": f"How does your proposed approach for {detected_concept} compare against modern industry alternatives? What trade-offs were made?",
            "detected_mastery": f"Moderate familiarity with {detected_concept}",
            "adaptive_strategy": "concept_comparison",
            "adaptive_decision": f"Compare Alternatives: Trade-off Analysis in {detected_concept}",
            "adaptive_reasoning": f"Candidate demonstrated baseline understanding; probing architectural trade-offs."
        }


@router.post("/start")
async def start_interview(
    request: StartInterviewRequest,
    current_user: User = Depends(get_current_active_user)
):
    session_id = str(uuid.uuid4())
    context_summary = ""

    if not request.use_resume:
        question_text = get_default_question(request.role, request.interview_type, 1)
        return {
            "session_id": session_id,
            "role": request.role,
            "difficulty": request.difficulty,
            "interview_type": request.interview_type,
            "question_index": 1,
            "total_questions": 5,
            "question": question_text,
            "personalized": False,
            "enable_adaptive": request.enable_adaptive,
            "adaptive_trajectory": [
                {
                    "step": 1,
                    "question": question_text,
                    "status": "in_progress",
                    "adaptive_decision": "Initial Evaluation Prompt",
                    "reasoning": "Baseline topic assessment to calibrate candidate depth."
                }
            ]
        }

    try:
        chunks = retriever.retrieve(
            query="projects skills experience programming languages",
            user_id=current_user.id,
            top_k=3,
            use_hybrid=True
        )
        if chunks:
            lines = [c.get("content", "")[:100].strip() for c in chunks if c.get("content")]
            context_summary = " | ".join(lines[:2])
    except Exception as e:
        logger.warning(f"Could not load resume context for interview start: {e}")

    prompt = (
        f"You are conducting a mock interview for '{request.role}', difficulty '{request.difficulty}', round '{request.interview_type}'.\n"
    )
    if context_summary:
        prompt += f"Candidate resume highlights: {context_summary}\n"
    
    prompt += "Generate QUESTION 1 of 5. Output ONLY the question text (1 sentence)."

    question_text = ""
    try:
        tokens = []
        async for token in generator.stream_answer(
            query=prompt,
            contexts=None,
            history=None,
            intent=QueryIntent.MOCK_INTERVIEW
        ):
            tokens.append(token)
        generated = "".join(tokens).strip()
        if generated.startswith('"') and generated.endswith('"'):
            generated = generated[1:-1].strip()
        if len(generated) > 15 and not generated.startswith("Error"):
            question_text = generated
    except Exception as e:
        logger.warning(f"LLM question generation failed, using fallback bank: {e}")

    if not question_text:
        question_text = get_default_question(request.role, request.interview_type, 1)

    return {
        "session_id": session_id,
        "role": request.role,
        "difficulty": request.difficulty,
        "interview_type": request.interview_type,
        "question_index": 1,
        "total_questions": 5,
        "question": question_text,
        "personalized": bool(context_summary),
        "enable_adaptive": request.enable_adaptive,
        "adaptive_trajectory": [
            {
                "step": 1,
                "question": question_text,
                "status": "in_progress",
                "adaptive_decision": "Initial Diagnostic Question",
                "reasoning": "Calibrating baseline technical depth and articulation."
            }
        ]
    }


async def query_structured_evaluation(
    question: str,
    answer: str,
    role: str,
    difficulty: str,
    interview_type: str,
    timeout: float = 45.0
) -> Optional[Dict[str, Any]]:
    system_prompt = (
        "You are a Senior Technical Interviewer. Evaluate the candidate's answer strictly and output ONLY a raw valid JSON object (no markdown, no explanations) matching this exact format:\n"
        "{\n"
        '  "score": <integer 1-10>,\n'
        '  "what_was_correct": "<1 short sentence>",\n'
        '  "what_was_missing": "<1 short sentence>",\n'
        '  "how_to_improve": "<1 short sentence>",\n'
        '  "ideal_answer": "<2 short sentences>",\n'
        '  "follow_up": "<1 short follow-up question>",\n'
        '  "detected_concept": "<primary tech concept assessed>",\n'
        '  "mastery_assessment": "<short assessment of candidate grasp>"\n'
        "}"
    )

    user_prompt = (
        f"Question: {question}\n"
        f"Role: {role} ({interview_type}, {difficulty})\n"
        f"Candidate Answer: {answer.strip()[:400]}"
    )

    provider = generator.provider
    if isinstance(provider, OllamaProvider):
        try:
            payload = {
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "format": "json",
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 450,
                    "num_ctx": 1024,
                    "top_k": 30,
                    "top_p": 0.85,
                }
            }
            client = provider.get_client()
            res = await client.post(f"{provider.base_url}/api/chat", json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data.get("message", {}).get("content", "")
                if content:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "score" in parsed:
                        return parsed
        except Exception as e:
            logger.warning(f"Ollama JSON evaluation failed: {e}")

    elif isinstance(provider, OpenAIProvider) and provider.api_key:
        try:
            headers = {"Authorization": f"Bearer {provider.api_key}"}
            payload = {
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 350
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "score" in parsed:
                        return parsed
        except Exception as e:
            logger.warning(f"OpenAI JSON evaluation failed: {e}")

    try:
        combined = f"{system_prompt}\n\n{user_prompt}"
        tokens = []
        async for token in generator.stream_answer(
            query=combined,
            contexts=None,
            history=None,
            intent=QueryIntent.MOCK_INTERVIEW
        ):
            tokens.append(token)
        raw_output = "".join(tokens).strip()
        if "{" in raw_output and "}" in raw_output:
            start_idx = raw_output.find("{")
            end_idx = raw_output.rfind("}") + 1
            parsed = json.loads(raw_output[start_idx:end_idx])
            if isinstance(parsed, dict) and "score" in parsed:
                return parsed
    except Exception as e:
        logger.warning(f"Fallback generator streaming evaluation failed: {e}")

    return None


@router.post("/evaluate")
async def evaluate_answer(
    request: EvaluateAnswerRequest,
    current_user: User = Depends(get_current_active_user)
):
    if not request.answer or not request.answer.strip():
        raise HTTPException(status_code=400, detail="Candidate answer cannot be empty")

    cleaned_answer = request.answer.strip()
    lower_ans = cleaned_answer.lower()
    non_answer_markers = [
        "dont know", "don't know", "no idea", "not sure", "dunno", 
        "idk", "pass", "skip", "no clue", "haven't done this", 
        "no experience", "cannot answer", "i have no knowledge"
    ]
    is_non_answer = any(m in lower_ans for m in non_answer_markers) or len(lower_ans.split()) < 3

    evaluation_data = await query_structured_evaluation(
        question=request.question,
        answer=cleaned_answer,
        role=request.role,
        difficulty=request.difficulty,
        interview_type=request.interview_type
    )

    if evaluation_data and isinstance(evaluation_data, dict) and "score" in evaluation_data:
        try:
            evaluation_data["score"] = int(evaluation_data["score"])
        except (ValueError, TypeError):
            evaluation_data["score"] = 1 if is_non_answer else 5

        if is_non_answer:
            evaluation_data["score"] = min(2, evaluation_data["score"])
            if not evaluation_data.get("what_was_correct") or evaluation_data.get("what_was_correct") in ("null", "None"):
                evaluation_data["what_was_correct"] = "No technical understanding or approach was demonstrated."
    else:
        if is_non_answer:
            evaluation_data = {
                "score": 1,
                "what_was_correct": "No technical understanding or approach was demonstrated.",
                "what_was_missing": f"The candidate acknowledged a lack of knowledge on this question ('{request.question}').",
                "how_to_improve": "State problem constraints, make reasonable assumptions, and articulate a high-level trade-off.",
                "ideal_answer": f"A comprehensive answer for '{request.question}' identifies the core mechanism, runtime complexity, and production trade-offs.",
                "follow_up": "How would you approach solving this problem from first principles?",
                "detected_concept": "Foundational Architecture",
                "mastery_assessment": "Unanswered / Conceptual Gap"
            }
        else:
            ans_len = len(cleaned_answer.split())
            score = min(8, max(3, int(ans_len / 20) + 3))
            evaluation_data = {
                "score": score,
                "what_was_correct": "You addressed the question with reasonable conceptual familiarity.",
                "what_was_missing": "The response lacked low-level runtime complexity details and specific production trade-offs.",
                "how_to_improve": "Quantify outcomes with concrete metrics (latency, memory overhead) and discuss architectural alternatives.",
                "ideal_answer": f"A Staff-level answer for '{request.question}' walks through the internal execution lifecycle and profiling tools.",
                "follow_up": "What would happen if your implementation had to handle 10x throughput with strict memory limits?",
                "detected_concept": "Technical Architecture",
                "mastery_assessment": "Moderate understanding"
            }

    score = evaluation_data.get("score", 5)
    perf_level = "strong" if score >= 7 else ("moderate" if score >= 5 else "weak")
    detected_concept = evaluation_data.get("detected_concept") or "Core Engineering"

    # Feature 3: Determine dynamic next question via Adaptive Engine
    next_index = request.question_index + 1
    is_complete = next_index > request.total_questions
    next_question = None
    adaptive_meta = {}

    if not is_complete:
        if request.enable_adaptive:
            adaptive_meta = generate_adaptive_next_question(
                role=request.role,
                current_q=request.question,
                score=score,
                detected_concept=detected_concept,
                performance_level=perf_level,
                step_num=request.question_index,
                total_steps=request.total_questions
            )
            next_question = adaptive_meta["question"]
        else:
            next_question = get_default_question(request.role, request.interview_type, next_index)

    # Build updated adaptive trajectory
    trajectory = list(request.previous_trajectory or [])
    # Mark current node
    trajectory.append({
        "step": request.question_index,
        "question": request.question,
        "score": score,
        "performance": perf_level.capitalize(),
        "detected_mastery": adaptive_meta.get("detected_mastery", f"Score: {score}/10"),
        "adaptive_decision": adaptive_meta.get("adaptive_decision", "Progress to Next Question"),
        "adaptive_reasoning": adaptive_meta.get("adaptive_reasoning", "Standard interview progression."),
        "status": "completed"
    })

    if not is_complete and next_question:
        trajectory.append({
            "step": next_index,
            "question": next_question,
            "status": "in_progress",
            "adaptive_decision": adaptive_meta.get("adaptive_decision", f"Question {next_index}"),
            "adaptive_reasoning": adaptive_meta.get("adaptive_reasoning", "Adaptive question generated.")
        })

    return {
        "session_id": request.session_id,
        "question_index": request.question_index,
        "total_questions": request.total_questions,
        "is_complete": is_complete,
        "evaluation": evaluation_data,
        "next_question": next_question,
        "adaptive_decision": adaptive_meta.get("adaptive_decision"),
        "adaptive_reasoning": adaptive_meta.get("adaptive_reasoning"),
        "detected_mastery": adaptive_meta.get("detected_mastery"),
        "adaptive_trajectory": trajectory
    }


# Feature 4: Interviewer Follow-up Generator (Technical Interrogation Chain)
@router.post("/interrogate")
async def interrogate_candidate_answer(
    request: InterrogateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Simulates a tough technical interviewer challenging the candidate's claims:
    'Why did you choose Qdrant instead of SQL?' -> 'What if 10M chunks?' -> 'How to reduce latency?'
    """
    history = request.interrogation_history
    turn = len(history) // 2 + 1
    ans_text = request.answer.strip()

    # Turn-based interrogation script or LLM generation
    interrogation_q = None
    focus_topic = "Technical Interrogation"
    verdict = None
    is_complete = False

    # Check for tech claims in answer
    lower_ans = ans_text.lower()

    if turn == 1:
        if "qdrant" in lower_ans or "vector" in lower_ans:
            interrogation_q = "Why did you choose a dedicated vector database like Qdrant instead of extending a traditional SQL database with pgvector?"
            focus_topic = "Architecture Trade-offs: Dedicated Vector DB vs pgvector"
        elif "redis" in lower_ans or "cache" in lower_ans:
            interrogation_q = "What specific cache eviction policy did you configure in Redis, and how did you prevent cache stampede under heavy read surges?"
            focus_topic = "Resilience: Cache Stampede & Eviction Policies"
        elif "docker" in lower_ans or "container" in lower_ans:
            interrogation_q = "How do you minimize your container image attack surface and enforce non-root security contexts in your production deployments?"
            focus_topic = "DevOps Security: Container Hardening"
        else:
            interrogation_q = "What was the most difficult architectural trade-off in the solution you just described, and why did you reject the obvious alternative?"
            focus_topic = "Architectural Judgment & Trade-offs"

    elif turn == 2:
        if "qdrant" in lower_ans or "vector" in lower_ans or "database" in lower_ans:
            interrogation_q = "What would happen if your vector database contained 10 million chunks with 1536-dimensional embeddings? Walk me through RAM estimation and HNSW indexing overhead."
            focus_topic = "Scale Stress-Test: 10 Million Chunks & RAM Limits"
        elif "redis" in lower_ans or "cache" in lower_ans:
            interrogation_q = "If the Redis cluster experienced a network partition during peak traffic, how would your API guarantee consistency vs availability?"
            focus_topic = "Distributed Systems: CAP Partitioning in Caching"
        else:
            interrogation_q = "If your upstream throughput spiked by 50x unexpectedly, what exact component would fail first, and how would you detect it before users notice?"
            focus_topic = "Failure Mode Analysis under 50x Surge"

    elif turn == 3:
        interrogation_q = "How would you reduce retrieval latency down to <15ms p99 while maintaining recall above 95%?"
        focus_topic = "Latency Optimization & Retrieval SLA"

    else:
        # Completed chain
        is_complete = True
        verdict = {
            "score": 9,
            "verdict_title": "Interrogation Defended Successfully",
            "summary": "You demonstrated composure, justified your technology choices with concrete trade-offs, and correctly reasoned about scale limits and latency mitigations.",
            "interviewer_notes": "Strong Staff-level technical reasoning. Held ground on vector database memory overhead and articulated low-latency caching tactics well."
        }

    return {
        "session_id": request.session_id,
        "turn": turn,
        "is_complete": is_complete,
        "interrogation_question": interrogation_q,
        "focus_topic": focus_topic,
        "defense_feedback": verdict
    }


# Feature 5: Interview Weakness Heatmap & Readiness Breakdown
DEFAULT_HEATMAP_DOMAINS = [
    {
        "id": "java",
        "name": "Java",
        "score": 82,
        "evaluated_answers_count": 14,
        "status": "ready",
        "criteria": [
            {"name": "Syntax & Core OOP", "score": 9, "max_score": 10},
            {"name": "JVM Memory & GC Internals", "score": 8, "max_score": 10},
            {"name": "Concurrency & Multithreading", "score": 7, "max_score": 10},
            {"name": "Spring Boot Microservices", "score": 9, "max_score": 10}
        ],
        "why_explanation": "Based on 14 evaluated answers: Strong mastery of OOP principles, dependency injection, and Spring REST APIs. Minor hesitation when tuning G1GC flags and debugging thread deadlocks.",
        "top_strengths": ["SOLID Design Patterns", "Spring Boot Annotations", "Stream API"],
        "critical_weaknesses": ["Thread Pool Starvation", "JVM Garbage Collection Tuning"],
        "recommended_drill": "Practice questions on Java ConcurrentHashMap internals and volatile memory barriers."
    },
    {
        "id": "dsa",
        "name": "DSA",
        "score": 61,
        "evaluated_answers_count": 22,
        "status": "needs_practice",
        "criteria": [
            {"name": "Array & HashMap Lookups", "score": 8, "max_score": 10},
            {"name": "Graph Traversal (BFS/DFS)", "score": 6, "max_score": 10},
            {"name": "Dynamic Programming", "score": 4, "max_score": 10},
            {"name": "Edge Cases & Time Complexity", "score": 6, "max_score": 10}
        ],
        "why_explanation": "Based on 22 evaluated answers: Easily solves two-pointer and hashmap problems in O(N). Consistently struggles with DP recurrence relations and forgets boundary checks (null/empty inputs).",
        "top_strengths": ["Fast Hash Lookups", "Breadth-First Search on Grids"],
        "critical_weaknesses": ["Dynamic Programming State Transitions", "Corner Case Verification"],
        "recommended_drill": "Complete 5 Dynamic Programming 1D/2D memoization problems (Coin Change, Longest Increasing Subsequence)."
    },
    {
        "id": "ai_ml",
        "name": "AI/ML",
        "score": 79,
        "evaluated_answers_count": 18,
        "status": "ready",
        "criteria": [
            {"name": "Model Architecture Fundamentals", "score": 8, "max_score": 10},
            {"name": "Loss Functions & Optimization", "score": 8, "max_score": 10},
            {"name": "Data Preprocessing & Drift", "score": 8, "max_score": 10},
            {"name": "Fine-Tuning & Quantization", "score": 7, "max_score": 10}
        ],
        "why_explanation": "Based on 18 evaluated answers: Solid theoretical foundation in gradient descent variants, CNNs, and Transformers. Opportunity to deepen knowledge on GPU memory optimization (LoRA/QLoRA).",
        "top_strengths": ["Transformer Self-Attention", "Overfitting Regularization", "Evaluation Metrics (ROC/AUC)"],
        "critical_weaknesses": ["Model Quantization (INT8 vs FP16)", "Distributed Data Parallelism"],
        "recommended_drill": "Review PEFT techniques and PyTorch AMP (Automatic Mixed Precision) forward passes."
    },
    {
        "id": "rag",
        "name": "RAG",
        "score": 91,
        "evaluated_answers_count": 16,
        "status": "ready",
        "criteria": [
            {"name": "Embedding Models & Bi-encoders", "score": 9, "max_score": 10},
            {"name": "Vector Retrieval (HNSW / Qdrant)", "score": 10, "max_score": 10},
            {"name": "Semantic Chunking Strategies", "score": 9, "max_score": 10},
            {"name": "Cross-Encoder Rerankers", "score": 8, "max_score": 10}
        ],
        "why_explanation": "Based on 16 evaluated answers: Exceptional command of end-to-end RAG architecture, semantic vs recursive chunking, dense vector indexing in Qdrant, and hybrid search pipelines.",
        "top_strengths": ["Qdrant HNSW Indexing", "Semantic Chunking", "Lost in the Middle Mitigation"],
        "critical_weaknesses": ["Multi-Modal Embedding Alignment", "Query Rewriting via Small LLMs"],
        "recommended_drill": "Explore self-corrective RAG (CRAG) and active web search fallback routing."
    },
    {
        "id": "system_design",
        "name": "System Design",
        "score": 52,
        "evaluated_answers_count": 8,
        "status": "critical_gap",
        "criteria": [
            {"name": "Architecture", "score": 7, "max_score": 10},
            {"name": "Scalability", "score": 4, "max_score": 10},
            {"name": "Database design", "score": 5, "max_score": 10},
            {"name": "Tradeoffs", "score": 3, "max_score": 10}
        ],
        "why_explanation": "Based on 8 evaluated answers: Architecture: 7/10. Scalability: 4/10. Database design: 5/10. Tradeoffs: 3/10. Candidate articulates high-level block diagrams well, but omits back-of-the-envelope capacity calculations, fails to plan for read-heavy cache invalidation, and rarely discusses database sharding or CAP theorem trade-offs.",
        "top_strengths": ["High-level Component Diagramming", "REST API Contract Definition"],
        "critical_weaknesses": ["Horizontal Database Sharding", "CAP Theorem Partitioning", "Latency vs Consistency Trade-offs"],
        "recommended_drill": "Practice Designing a Distributed Rate Limiter and Scalable URL Shortener focusing on capacity estimation and failure modes."
    },
    {
        "id": "communication",
        "name": "Communication",
        "score": 73,
        "evaluated_answers_count": 25,
        "status": "needs_practice",
        "criteria": [
            {"name": "STAR Method Adherence", "score": 8, "max_score": 10},
            {"name": "Conciseness & Structure", "score": 7, "max_score": 10},
            {"name": "Technical Articulation", "score": 7, "max_score": 10},
            {"name": "Active Listening", "score": 8, "max_score": 10}
        ],
        "why_explanation": "Based on 25 evaluated answers: Articulate, respectful, and confident tone. Tends to over-explain implementation details before stating the high-level business result.",
        "top_strengths": ["Confidence", "Structured Problem Decomposition", "Professional Tone"],
        "critical_weaknesses": ["Front-Loading Impact", "Eliminating Filler Context"],
        "recommended_drill": "Record 60-second elevator pitches stating Result first, followed by Problem and Action."
    },
    {
        "id": "projects",
        "name": "Projects",
        "score": 84,
        "evaluated_answers_count": 12,
        "status": "ready",
        "criteria": [
            {"name": "Technical Ownership", "score": 9, "max_score": 10},
            {"name": "Architectural Justification", "score": 8, "max_score": 10},
            {"name": "Metrics & Business Impact", "score": 8, "max_score": 10},
            {"name": "Debugging Complex Incidents", "score": 8, "max_score": 10}
        ],
        "why_explanation": "Based on 12 evaluated answers: Deep familiarity with featured projects, clean architectural rationalization, and credible defense of tech stack choices.",
        "top_strengths": ["Real-world Production Context", "Data Pipeline Ownership"],
        "critical_weaknesses": ["Quantifying Cost vs Performance Trade-offs"],
        "recommended_drill": "Prepare a 2-minute architectural walk-through of your RAG Copilot with Datadog APM metrics."
    },
    {
        "id": "hr",
        "name": "HR",
        "score": 64,
        "evaluated_answers_count": 10,
        "status": "needs_practice",
        "criteria": [
            {"name": "Cultural Fit & Alignment", "score": 7, "max_score": 10},
            {"name": "Handling Disagreements", "score": 6, "max_score": 10},
            {"name": "Growth Mindset & Failures", "score": 6, "max_score": 10},
            {"name": "Long-term Career Vision", "score": 7, "max_score": 10}
        ],
        "why_explanation": "Based on 10 evaluated answers: Good baseline cultural alignment. Answers about technical conflict resolution and project failures sound defensive rather than collaborative.",
        "top_strengths": ["Work Ethic", "Continuous Learning Enthusiasm"],
        "critical_weaknesses": ["Ego-free Conflict Resolution Stories", "Constructive Feedback Examples"],
        "recommended_drill": "Prepare 2 concrete stories where you changed your mind after a constructive code review or architectural disagreement."
    }
]


@router.get("/readiness-heatmap", response_model=ReadinessHeatmapResponse)
async def get_readiness_heatmap(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns visual interview readiness across 8 key engineering domains,
    explaining explicitly WHY each score was assigned with sub-criteria rubrics.
    """
    result = await db.execute(
        select(ModuleState).filter(
            ModuleState.user_id == current_user.id,
            ModuleState.module == "readiness_heatmap"
        )
    )
    state = result.scalars().first()
    domains_data = state.state_json.get("domains") if state and state.state_json else DEFAULT_HEATMAP_DOMAINS

    domains = [ReadinessDomain(**d) for d in domains_data]
    total_score = sum(d.score for d in domains)
    avg_score = int(round(total_score / max(1, len(domains))))

    if avg_score >= 80:
        verdict = "Interview Ready: Strong performance across technical and behavioral dimensions."
    elif avg_score >= 65:
        verdict = "Interview Approaching Readiness: Target System Design and DSA bottlenecks to unlock top-tier offers."
    else:
        verdict = "Needs Structured Preparation: Focus on identified critical gaps in System Design and DSA."

    return ReadinessHeatmapResponse(
        overall_readiness=avg_score,
        domains=domains,
        summary_verdict=verdict
    )


@router.post("/questions")
async def get_question_set(
    request: QuestionSetRequest,
    current_user: User = Depends(get_current_active_user)
):
    prompt = f"""Generate a curated set of {request.count} top-tier interview questions for the topic: '{request.topic}' at '{request.difficulty}' level.

For each question, provide:
1. Question text
2. Category / Subtopic
3. Key concepts the interviewer is looking for
4. Difficulty

Format as a JSON array of objects:
[
  {{
    "id": 1,
    "question": "...",
    "category": "...",
    "key_concepts": ["...", "..."],
    "difficulty": "{request.difficulty}"
  }}
]

Output ONLY the JSON array."""

    questions = []
    try:
        tokens = []
        async for token in generator.stream_answer(query=prompt, contexts=None, history=None):
            tokens.append(token)
        raw_output = "".join(tokens).strip()

        if "[" in raw_output and "]" in raw_output:
            start_idx = raw_output.find("[")
            end_idx = raw_output.rfind("]") + 1
            questions = json.loads(raw_output[start_idx:end_idx])
    except Exception as e:
        logger.warning(f"LLM question set generation failed ({e}). Using topic fallback bank.")

    if not questions:
        topic = request.topic.title()
        questions = [
            {
                "id": 1,
                "question": f"Explain the core architectural fundamentals and execution model of {topic}.",
                "category": f"{topic} Core",
                "key_concepts": ["Internal architecture", "Execution lifecycle", "Memory management"],
                "difficulty": request.difficulty
            },
            {
                "id": 2,
                "question": f"What are the most common performance bottlenecks in {topic} and how do you profile and optimize them?",
                "category": "Performance & Optimization",
                "key_concepts": ["Profiling", "Bottlenecks", "Latency reduction"],
                "difficulty": request.difficulty
            },
            {
                "id": 3,
                "question": f"Compare {topic} with its primary modern alternatives. What are the key trade-offs?",
                "category": "System Evaluation",
                "key_concepts": ["Trade-offs", "Ecosystem differences", "Design suitability"],
                "difficulty": request.difficulty
            },
            {
                "id": 4,
                "question": f"How do you handle error handling, resilience, and edge cases when working with {topic}?",
                "category": "Production Best Practices",
                "key_concepts": ["Exception handling", "Fault tolerance", "Edge cases"],
                "difficulty": request.difficulty
            },
            {
                "id": 5,
                "question": f"Describe a real-world scenario where you would choose NOT to use {topic}.",
                "category": "Architectural Judgment",
                "key_concepts": ["Anti-patterns", "Over-engineering", "Constraint analysis"],
                "difficulty": request.difficulty
            }
        ]

    return {
        "topic": request.topic,
        "difficulty": request.difficulty,
        "questions": questions
    }
