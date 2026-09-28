import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class KnowledgeMode(str, Enum):
    AUTO = "auto"
    DOCUMENT = "document"
    EDUCATION = "education"
    INTERVIEW = "interview"

class QueryIntent(str, Enum):
    DOCUMENT_QA = "DOCUMENT_QA"
    GENERAL_EDUCATION = "GENERAL_EDUCATION"
    INTERVIEW_PREPARATION = "INTERVIEW_PREPARATION"
    PROJECT_INTERVIEW = "PROJECT_INTERVIEW"
    CODING_PROBLEM = "CODING_PROBLEM"
    MOCK_INTERVIEW = "MOCK_INTERVIEW"
    CAREER_GUIDANCE = "CAREER_GUIDANCE"

# Explicit resume / uploaded document markers
DOCUMENT_EXPLICIT_PATTERNS = [
    r'\bin my (resume|cv|document|file|uploaded file|profile)\b',
    r'\bfrom my (resume|cv|document|file|uploaded file)\b',
    r'\bin the (resume|cv|document|uploaded file)\b',
    r'\bmy (cgpa|gpa|marks|percentage|college|university|school|grade)\b',
    r'\bwhat cgpa\b',
    r'\bmy contact|my phone|my email|my address\b',
    r'\bwhat is (not|unmentioned) in my (resume|document)\b',
    r'\bwhat projects (have i worked on|are in my resume|did i do|have i done)\b',
    r'\bwhat projects\b',
    r'\btell me about all my projects\b',
    r'\btell me about (my |the )?(placemate|innovest|hybrid ai|chemotherapy|internship)\b',
    r'\b(placemate|innovest|chemotherapy|hybrid ai)\b',
    r'\bwhat certifications do i have\b',
    r'\bwhat skills (are mentioned in my|do i have in my|are in my) resume\b',
    r'\bsummarize my resume\b',
    r'\bmy internship\b',
    r'\bwhich project used\b',
    r'\bwhich project is related to\b',
]

# Educational / Conceptual markers
EDUCATION_PATTERNS = [
    r'^\s*explain\b',
    r'^\s*teach me\b',
    r'^\s*what is (the difference between|a|an|the|polymorphism|rag|fine-tuning|embedding|transformer|fastapi|docker|jwt|recursion)\b',
    r'^\s*how (does|do|can|to)\b',
    r'\bhow (a |an |the )?(transformer|neural network|rag|model|database|llm) works?\b',
    r'\bconcepts?\b',
    r'\btutorial\b',
    r'\bdefinition of\b',
    r'\bcompare\b',
    r'\bdifference between\b',
    r'\bpros and cons of\b',
    r'\boop concepts?\b',
    r'\bpolymorphism\b',
    r'\bencapsulation\b',
    r'\binheritance\b',
    r'\babstraction\b',
]

# Coding / Problem solving markers
CODING_PATTERNS = [
    r'\b(coding|leetcode|dsa)\b',
    r'\b(array|string|linked list|binary tree|graph|dynamic programming|dp|two pointers?)\s+(problem|question|challenge)\b',
    r'\b(give me|ask me|solve)\s+(a\s+)?(coding|dsa|java|python|c\+\+|sql|array|string)?\s*(problem|question|challenge)\b',
    r'\bwrite (a program|code|a function|an algorithm)\b',
    r'\bsolve this\b',
    r'\btwo pointers?\b',
    r'\bbinary search\b',
]

# Mock Interview markers
MOCK_INTERVIEW_PATTERNS = [
    r'\bact as (my |an |a )?interviewer\b',
    r'\bmock interview\b',
    r'\bsimulate (an? |my )?interview\b',
    r'\binterview me\b',
    r'\bstart (the |a )?interview\b',
    r'\bbegin (the |a )?interview\b',
    r'\bask me (a |an |one )?question at a time\b',
]

# Project Interview markers
PROJECT_INTERVIEW_PATTERNS = [
    r'\bquestions? (can an interviewer ask|about my project)\b',
    r'\bask me questions? about (placemate|innovest|hybrid ai|chemotherapy|my project)\b',
    r'\bhow (do|can) i explain (placemate|innovest|hybrid ai|chemotherapy|my project) in an interview\b',
    r'\bproject interview questions?\b',
    r'\bdefend my project\b',
]

# General Interview Preparation markers
INTERVIEW_PREP_PATTERNS = [
    r'\btrain me for (my |an? )?(interview|ai/ml interview|technical interview)\b',
    r'\bprepare me for (my |an? )?(interview|ai/ml interview|technical interview)\b',
    r'\bprepare questions based on my resume\b',
    r'\binterview questions? (based on my resume|for my resume)\b',
    r'\bgive me (java|python|sql|ai|ml|dsa|system design|react|fastapi|backend) interview questions\b',
    r'\binterview prep(aration)?\b',
    r'\binterview questions?\b',
    r'\bround \d\b',
    r'\bbehavioral questions?\b',
    r'\bhr questions?\b',
]

# Career Guidance markers
CAREER_GUIDANCE_PATTERNS = [
    r'\bcareer (roadmap|advice|path|progression|guidance)\b',
    r'\bhow (do|can) i become a\b',
    r'\bwhat should i learn next\b',
    r'\btransition to\b',
    r'\bprepare for faang\b',
]


def classify_intent(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: Optional[str] = "auto"
) -> QueryIntent:
    """
    Classifies the user query intent to select the optimal pipeline:
    - DOCUMENT_QA: Grounded RAG with strict document citation.
    - GENERAL_EDUCATION: Pure LLM technical tutor (no unnecessary RAG, fast).
    - INTERVIEW_PREPARATION: Personalized RAG + General LLM knowledge.
    - PROJECT_INTERVIEW: Resume project RAG + General technical questioning.
    - CODING_PROBLEM: Algorithms/coding problem practice.
    - MOCK_INTERVIEW: Live sequential multi-round interview simulation.
    - CAREER_GUIDANCE: Strategic career and learning path coaching.
    """
    q = query.lower().strip()
    m = (mode or "auto").lower()

    # 1. Direct Mode Overrides
    if m == KnowledgeMode.DOCUMENT.value:
        return QueryIntent.DOCUMENT_QA

    # 2. Check for Explicit Document/Resume questions FIRST
    if any(re.search(p, q) for p in DOCUMENT_EXPLICIT_PATTERNS):
        return QueryIntent.DOCUMENT_QA

    # 3. Check for explicit Mock Interview requests
    if any(re.search(p, q) for p in MOCK_INTERVIEW_PATTERNS):
        return QueryIntent.MOCK_INTERVIEW

    # 4. Check for Project-specific Interview questions
    if any(re.search(p, q) for p in PROJECT_INTERVIEW_PATTERNS):
        return QueryIntent.PROJECT_INTERVIEW

    # 5. General Education check: If query asks "explain X", "what is X", "how does X work",
    # and has NO explicit resume markers, route directly to GENERAL_EDUCATION (0ms RAG)
    if any(re.search(p, q) for p in EDUCATION_PATTERNS) or q.startswith(("explain ", "teach me ", "what is ", "how do ", "how does ", "why do ", "why does ")):
        if not re.search(r'\bmy (resume|cv|document|file|uploaded file|profile|project|internship|skills?|experience)\b', q):
            return QueryIntent.GENERAL_EDUCATION

    # 6. Check for Coding / DSA problem requests
    if any(re.search(p, q) for p in CODING_PATTERNS):
        return QueryIntent.CODING_PROBLEM

    # 7. Check for Interview Preparation requests
    if any(re.search(p, q) for p in INTERVIEW_PREP_PATTERNS):
        return QueryIntent.INTERVIEW_PREPARATION

    # 8. Check for Career Guidance requests
    if any(re.search(p, q) for p in CAREER_GUIDANCE_PATTERNS):
        return QueryIntent.CAREER_GUIDANCE

    # 9. Mode specific fallbacks
    if m == KnowledgeMode.EDUCATION.value:
        return QueryIntent.GENERAL_EDUCATION
    if m == KnowledgeMode.INTERVIEW.value:
        return QueryIntent.INTERVIEW_PREPARATION

    # 10. Conversational Context Inspection (Multi-turn continuity)
    if history and len(history) > 0:
        last_turn = history[-1]
        last_content = last_turn.get("content", "").lower()
        if any(w in last_content for w in ["explain", "interview", "question", "polymorphism", "concept", "what is"]):
            if len(q.split()) <= 4:
                return QueryIntent.GENERAL_EDUCATION

    # Default to GENERAL_EDUCATION for general chat rather than expensive RAG
    return QueryIntent.GENERAL_EDUCATION

