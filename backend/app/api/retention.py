import math
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.models.module_state import ModuleState
from app.rag.generator import generator

logger = logging.getLogger(__name__)
router = APIRouter()

# Default seed skills with practice dates if user has none yet
DEFAULT_RETENTION_SKILLS = [
    {
        "skill": "RAG",
        "category": "AI/ML",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
        "initial_strength": 92,
        "half_life_days": 10,
        "revision_scheduled": None,
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"), "score": 92}
        ]
    },
    {
        "skill": "PyTorch",
        "category": "Deep Learning",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=12)).strftime("%Y-%m-%d"),
        "initial_strength": 80,
        "half_life_days": 8,
        "revision_scheduled": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d"),
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=12)).strftime("%Y-%m-%d"), "score": 80}
        ]
    },
    {
        "skill": "System Design",
        "category": "Architecture",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d"),
        "initial_strength": 75,
        "half_life_days": 7,
        "revision_scheduled": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d"), "score": 75}
        ]
    },
    {
        "skill": "Python",
        "category": "Programming",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"),
        "initial_strength": 96,
        "half_life_days": 25,
        "revision_scheduled": None,
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"), "score": 96}
        ]
    },
    {
        "skill": "Docker",
        "category": "DevOps",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=18)).strftime("%Y-%m-%d"),
        "initial_strength": 70,
        "half_life_days": 6,
        "revision_scheduled": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=18)).strftime("%Y-%m-%d"), "score": 70}
        ]
    },
    {
        "skill": "DSA - Graphs & DP",
        "category": "Algorithms",
        "last_practiced": (datetime.now(timezone.utc) - timedelta(days=9)).strftime("%Y-%m-%d"),
        "initial_strength": 85,
        "half_life_days": 8,
        "revision_scheduled": None,
        "history": [
            {"date": (datetime.now(timezone.utc) - timedelta(days=9)).strftime("%Y-%m-%d"), "score": 85}
        ]
    }
]

def calculate_ebbinghaus_retention(last_practiced_str: str, initial_strength: int = 90, half_life_days: float = 10.0) -> Dict[str, Any]:
    """
    Computes memory retention using the Ebbinghaus exponential decay model:
    R = S * e^(-t / tau)
    where tau = half_life / ln(2)
    """
    try:
        last_date = datetime.strptime(last_practiced_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_elapsed = max(0, (now - last_date).days)
    except Exception:
        days_elapsed = 5

    decay_constant = half_life_days / 0.693147  # ln(2)
    decay_factor = math.exp(-days_elapsed / decay_constant)
    current_retention = max(15, min(100, int(round(initial_strength * decay_factor))))

    if current_retention >= 85:
        status = "fresh"
        status_label = "Optimal Retention"
        color = "emerald"
    elif current_retention >= 65:
        status = "degrading"
        status_label = "Decaying (Practice Soon)"
        color = "amber"
    else:
        status = "critical"
        status_label = "Critical Decay (Immediate Revision)"
        color = "rose"

    needs_test = days_elapsed >= 4

    return {
        "days_elapsed": days_elapsed,
        "current_retention": current_retention,
        "decay_status": status,
        "status_label": status_label,
        "color": color,
        "needs_test": needs_test
    }

class RetentionSkillModel(BaseModel):
    skill: str
    category: str
    last_practiced: str
    days_elapsed: int
    current_retention: int
    decay_status: str
    status_label: str
    color: str
    needs_test: bool
    revision_scheduled: Optional[str] = None

class RetentionOverviewResponse(BaseModel):
    overall_retention: int
    skills: List[RetentionSkillModel]
    prompt_notification: Optional[Dict[str, Any]] = None

class StartRetentionTestRequest(BaseModel):
    skill: str

class TestQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str

class RetentionTestResponse(BaseModel):
    skill: str
    time_limit_seconds: int = 180
    questions: List[TestQuestion]

class SubmitRetentionTestRequest(BaseModel):
    skill: str
    answers: List[int]  # Selected option indices for each question

class SubmitRetentionTestResponse(BaseModel):
    skill: str
    score_percentage: int
    old_retention: int
    new_retention: int
    revision_scheduled: Optional[str]
    feedback: str
    targeted_revision_questions: List[str]

# Pre-curated high-impact retention questions for fast instant feedback
CURATED_RETENTION_QUESTIONS: Dict[str, List[Dict[str, Any]]] = {
    "RAG": [
        {
            "id": 1,
            "question": "What is the primary role of a Cross-Encoder Reranker in a modern two-stage RAG pipeline?",
            "options": [
                "Generates vector embeddings for documents at ingestion time",
                "Re-scores top-k candidate chunks by computing joint query-chunk cross-attention",
                "Splits long documents into fixed-size character windows",
                "Performs keyword BM25 token hashing"
            ],
            "correct_option_index": 1,
            "explanation": "A cross-encoder reranker processes the query and chunk simultaneously via full cross-attention, accurately scoring semantic relevance after fast bi-encoder retrieval."
        },
        {
            "id": 2,
            "question": "Why is Semantic Chunking often superior to fixed character chunking for technical documentation?",
            "options": [
                "It uses less RAM during database indexing",
                "It splits documents strictly every 500 characters",
                "It preserves coherent conceptual boundaries by monitoring embedding distance between consecutive sentences",
                "It eliminates the need for vector databases entirely"
            ],
            "correct_option_index": 2,
            "explanation": "Semantic chunking monitors similarity drops between sentences to ensure chunks contain complete standalone thoughts rather than fragmented code or sentences."
        },
        {
            "id": 3,
            "question": "In production RAG, what is the 'Lost in the Middle' phenomenon and how is it mitigated?",
            "options": [
                "LLMs struggle to retrieve knowledge placed in the middle of long context windows; mitigated by reranking most relevant chunks to top and bottom",
                "Vector database indexes drop chunks with intermediate IDs; mitigated by sharding",
                "Documents lose markdown formatting; mitigated by regex cleaning",
                "Network packets get dropped between client and server; mitigated by TCP retries"
            ],
            "correct_option_index": 0,
            "explanation": "Research shows LLMs attend most strongly to the beginning and end of the prompt context window. Placing high-relevance chunks at the periphery mitigates this."
        }
    ],
    "PyTorch": [
        {
            "id": 1,
            "question": "Why must you call `optimizer.zero_grad()` before executing `loss.backward()` in a PyTorch training loop?",
            "options": [
                "To reset the model weights to Gaussian random values",
                "Because PyTorch accumulates gradients in `.grad` by default on each backward pass",
                "To clear GPU memory cache and prevent CUDA out-of-memory errors",
                "To freeze the batch normalization moving averages"
            ],
            "correct_option_index": 1,
            "explanation": "PyTorch accumulates gradients by design (useful for RNNs or gradient accumulation across mini-batches). Without zero_grad(), gradients keep adding up."
        },
        {
            "id": 2,
            "question": "What is the key functional difference between `model.eval()` and `torch.no_grad()`?",
            "options": [
                "They are 100% identical and can be used interchangeably",
                "`model.eval()` toggles layers like Dropout & BatchNorm to evaluation mode; `torch.no_grad()` disables the autograd computation graph engine",
                "`torch.no_grad()` quantizes model parameters to FP16",
                "`model.eval()` offloads tensors from VRAM to CPU"
            ],
            "correct_option_index": 1,
            "explanation": "model.eval() alters behavior of specific modules (BatchNorm uses running stats, Dropout is turned off). torch.no_grad() prevents tracking gradient history to save memory."
        },
        {
            "id": 3,
            "question": "What problem does mixed precision training with `torch.cuda.amp.autocast()` solve?",
            "options": [
                "Speeds up computation and cuts memory usage by using FP16/BF16 where safe while preserving numerical stability in FP32",
                "Automatically tunes learning rates across epochs",
                "Distributes tensors across multiple physical nodes",
                "Replaces Adam with SGD automatically"
            ],
            "correct_option_index": 0,
            "explanation": "AMP accelerates matrix operations using Tensor Cores in half precision (FP16/BF16) and uses a GradScaler to prevent gradient underflow."
        }
    ],
    "System Design": [
        {
            "id": 1,
            "question": "What is the primary difference between Strong Consistency and Eventual Consistency in distributed data stores?",
            "options": [
                "Strong consistency allows stale reads; eventual consistency never allows stale reads",
                "Strong consistency guarantees all nodes see the latest write immediately at the cost of higher latency/lower availability; eventual consistency guarantees replicas converge over time",
                "Strong consistency only works on single-threaded CPUs",
                "Eventual consistency requires two-phase commit on every read"
            ],
            "correct_option_index": 1,
            "explanation": "According to the CAP theorem, Strong Consistency forces reads to return the latest write across replicas, sacrificing partition latency or write availability."
        },
        {
            "id": 2,
            "question": "In high-throughput microservices, how does the Circuit Breaker pattern protect downstream services?",
            "options": [
                "It compresses all HTTP payloads using gzip",
                "It stops sending requests to a failing service after a failure threshold, allowing the degraded dependency time to recover",
                "It encrypts database credentials at rest",
                "It routes all traffic through a single master node"
            ],
            "correct_option_index": 1,
            "explanation": "Circuit breakers transition from Closed to Open when failures cross a threshold, quickly failing fast without exacerbating cascading failures in downstream systems."
        },
        {
            "id": 3,
            "question": "What is the primary benefit of Consistent Hashing with virtual nodes in distributed caching (e.g. Memcached/DynamoDB)?",
            "options": [
                "Eliminates network latency completely",
                "Minimizes key redistribution when nodes are added or removed, while virtual nodes ensure balanced load distribution",
                "Guarantees ACID transactions across shards",
                "Replaces TCP with UDP for packet delivery"
            ],
            "correct_option_index": 1,
            "explanation": "Consistent hashing requires remapping only k/N keys on node addition/removal, and virtual nodes prevent hot spots by evenly dispersing partitions."
        }
    ]
}

async def get_user_retention_data(user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(ModuleState).filter(
            ModuleState.user_id == user_id,
            ModuleState.module == "skill_retention"
        )
    )
    state = result.scalars().first()
    if state and state.state_json and "skills" in state.state_json:
        return state.state_json["skills"]
    return DEFAULT_RETENTION_SKILLS

async def save_user_retention_data(user_id: int, skills: List[Dict[str, Any]], db: AsyncSession):
    result = await db.execute(
        select(ModuleState).filter(
            ModuleState.user_id == user_id,
            ModuleState.module == "skill_retention"
        )
    )
    state = result.scalars().first()
    if state:
        state.state_json = {"skills": skills, "updated_at": datetime.now(timezone.utc).isoformat()}
    else:
        state = ModuleState(
            user_id=user_id,
            module="skill_retention",
            state_json={"skills": skills, "updated_at": datetime.now(timezone.utc).isoformat()}
        )
        db.add(state)
    await db.commit()

@router.get("/status", response_model=RetentionOverviewResponse)
async def get_retention_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    skills_data = await get_user_retention_data(current_user.id, db)
    processed_skills: List[RetentionSkillModel] = []
    total_retention = 0

    prompt_candidate = None

    for item in skills_data:
        calc = calculate_ebbinghaus_retention(
            item.get("last_practiced", "2026-09-20"),
            item.get("initial_strength", 90),
            item.get("half_life_days", 10.0)
        )
        skill_model = RetentionSkillModel(
            skill=item["skill"],
            category=item.get("category", "General"),
            last_practiced=item.get("last_practiced", "2026-09-20"),
            days_elapsed=calc["days_elapsed"],
            current_retention=calc["current_retention"],
            decay_status=calc["decay_status"],
            status_label=calc["status_label"],
            color=calc["color"],
            needs_test=calc["needs_test"],
            revision_scheduled=item.get("revision_scheduled")
        )
        processed_skills.append(skill_model)
        total_retention += calc["current_retention"]

        # Pick the most critically decaying skill for prompt
        if calc["decay_status"] in ("critical", "degrading") and not prompt_candidate:
            prompt_candidate = {
                "skill": item["skill"],
                "last_practiced": item.get("last_practiced", "2026-09-20"),
                "days_ago": calc["days_elapsed"],
                "retention": calc["current_retention"],
                "message": f"Quick 3-minute {item['skill']} retention test? You learned it on {item.get('last_practiced', 'recently')} ({calc['days_elapsed']} days ago). Retention has decayed to {calc['current_retention']}%."
            }

    avg_retention = int(round(total_retention / max(1, len(processed_skills))))

    return RetentionOverviewResponse(
        overall_retention=avg_retention,
        skills=processed_skills,
        prompt_notification=prompt_candidate
    )

@router.post("/test", response_model=RetentionTestResponse)
async def start_retention_test(
    request: StartRetentionTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    skill = request.skill.strip()
    questions_data = CURATED_RETENTION_QUESTIONS.get(skill)

    if not questions_data:
        # Check case-insensitive match
        for k in CURATED_RETENTION_QUESTIONS:
            if k.lower() in skill.lower() or skill.lower() in k.lower():
                questions_data = CURATED_RETENTION_QUESTIONS[k]
                break

    if not questions_data:
        # Dynamic fallback test questions for any topic
        questions_data = [
            {
                "id": 1,
                "question": f"What is the foundational architectural principle behind {skill}?",
                "options": [
                    f"Decoupled modular abstraction and low-coupling design in {skill}",
                    f"Monolithic linear memory execution without abstraction",
                    f"Bypassing all runtime type validation",
                    f"Strictly client-side thread management"
                ],
                "correct_option_index": 0,
                "explanation": f"In {skill}, decoupling concerns and maintaining modular separation of logic ensures maintainability and scalability."
            },
            {
                "id": 2,
                "question": f"When profiling bottlenecks in {skill}, what metric is most critical in high-load production?",
                "options": [
                    "Lines of code written per sprint",
                    "p99 latency, garbage collection pauses, and throughput under peak concurrency",
                    "Number of Git branch merges",
                    "HTML DOM rendering time"
                ],
                "correct_option_index": 1,
                "explanation": "Production observability prioritizes p99 tail latency and resource saturation to prevent cascading outages."
            },
            {
                "id": 3,
                "question": f"What is an anti-pattern when implementing {skill} in microservices?",
                "options": [
                    "Writing comprehensive integration tests",
                    "Tight synchronous coupling without timeouts or fallback circuit breakers",
                    "Using structured JSON logging",
                    "Employing automated CI/CD pipelines"
                ],
                "correct_option_index": 1,
                "explanation": "Synchronous chains without circuit breakers lead to thread pool exhaustion when a downstream dependency stalls."
            }
        ]

    return RetentionTestResponse(
        skill=skill,
        time_limit_seconds=180,
        questions=[TestQuestion(**q) for q in questions_data]
    )

@router.post("/evaluate", response_model=SubmitRetentionTestResponse)
async def evaluate_retention_test(
    request: SubmitRetentionTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    skill = request.skill.strip()
    skills_data = await get_user_retention_data(current_user.id, db)

    # Find the skill entry
    target_skill_idx = None
    for idx, item in enumerate(skills_data):
        if item["skill"].lower() == skill.lower():
            target_skill_idx = idx
            break

    # Find correct answers
    q_data = CURATED_RETENTION_QUESTIONS.get(skill)
    if not q_data:
        for k in CURATED_RETENTION_QUESTIONS:
            if k.lower() in skill.lower() or skill.lower() in k.lower():
                q_data = CURATED_RETENTION_QUESTIONS[k]
                break

    correct_count = 0
    total_q = len(request.answers)
    if q_data and len(q_data) == total_q:
        for idx, chosen_opt in enumerate(request.answers):
            if chosen_opt == q_data[idx]["correct_option_index"]:
                correct_count += 1
    else:
        # Default scoring
        correct_count = sum(1 for a in request.answers if a in (0, 1))

    score_pct = int(round((correct_count / max(1, total_q)) * 100))

    # Calculate old and new retention
    old_item = skills_data[target_skill_idx] if target_skill_idx is not None else None
    old_calc = calculate_ebbinghaus_retention(
        old_item.get("last_practiced", "2026-09-20") if old_item else "2026-09-20",
        old_item.get("initial_strength", 85) if old_item else 85,
        old_item.get("half_life_days", 10.0) if old_item else 10.0
    )
    old_retention = old_calc["current_retention"]

    # Updated retention: if high score, memory boost! If low score, decay accelerates
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if score_pct >= 70:
        new_retention = min(100, max(old_retention + 25, score_pct))
        revision_date = None
        feedback = f"Great work! You scored {score_pct}%. Your {skill} memory retention is restored to {new_retention}%."
        targeted_drills = [
            f"Review advanced production edge-cases in {skill}.",
            f"Explore benchmark optimizations for high concurrency {skill} workflows."
        ]
    else:
        # Poor performance: decay drops, schedule immediate revision!
        new_retention = max(20, min(old_retention - 15, score_pct))
        revision_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
        feedback = f"Retention alert: You scored {score_pct}% ({correct_count}/{total_q} correct). Retention dropped to {new_retention}%. Automatic revision scheduled for {revision_date}."
        targeted_drills = [
            f"Core fundamentals drill: Re-study {skill} baseline definitions and mechanisms.",
            f"Comparative analysis: Why common assumptions fail in {skill} under high concurrency.",
            f"Hands-on implementation: Build a minimal {skill} prototype from scratch to reinforce tactile memory."
        ]

    # Update in persistent state
    if target_skill_idx is not None:
        skills_data[target_skill_idx]["last_practiced"] = today_str
        skills_data[target_skill_idx]["initial_strength"] = new_retention
        skills_data[target_skill_idx]["revision_scheduled"] = revision_date
        history = list(skills_data[target_skill_idx].get("history", []))
        history.append({"date": today_str, "score": score_pct})
        skills_data[target_skill_idx]["history"] = history
    else:
        skills_data.append({
            "skill": skill,
            "category": "Technical",
            "last_practiced": today_str,
            "initial_strength": new_retention,
            "half_life_days": 10,
            "revision_scheduled": revision_date,
            "history": [{"date": today_str, "score": score_pct}]
        })

    await save_user_retention_data(current_user.id, skills_data, db)

    return SubmitRetentionTestResponse(
        skill=skill,
        score_percentage=score_pct,
        old_retention=old_retention,
        new_retention=new_retention,
        revision_scheduled=revision_date,
        feedback=feedback,
        targeted_revision_questions=targeted_drills
    )
