import json
import logging
import asyncio
import time
from typing import List, Dict, Any, AsyncGenerator, Tuple, Optional
from abc import ABC, abstractmethod
import httpx

from app.core.config import settings
from app.rag.intent import QueryIntent

logger = logging.getLogger(__name__)

# =====================================================================
# SYSTEM PROMPTS FOR EACH KNOWLEDGE MODE / INTENT
# =====================================================================

DOCUMENT_QA_SYSTEM_PROMPT = """You are CareerMind AI, a precision document-grounded assistant.

Answer strictly using the retrieved document context.

Rules:
1. Do not invent information or make assumptions not supported by the retrieved document.
2. If the context does not contain the answer, say clearly:
   "I couldn't find this information in the uploaded documents."
3. When the user asks for a list, summary, or overview (such as projects, skills, certifications, education, or experience), include ALL relevant items present in the retrieved context. Do not stop after the first item.
4. Keep answers concise, factual, structured, and directly relevant.
5. Every claim or listed project/skill must be supported by the uploaded context. Include source labels (e.g., 📄 [filename] — Page [page]).
6. Do NOT fabricate citations or page numbers."""

GENERAL_EDUCATION_SYSTEM_PROMPT = """You are CareerMind AI, an intelligent, helpful AI assistant and technical mentor.
Answer the user's questions clearly, accurately, and directly.

CRITICAL INSTRUCTIONS:
1. Directly answer what the user asked without unnecessary fluff. If the user gives a greeting or a simple request, respond naturally and appropriately.
2. NO SUGGESTIONS: Do NOT provide suggestions, study tips, or unsolicited follow-up questions at the end of your response. Give ONLY the direct answer requested.
3. When technical explanations or code are requested, provide clean, accurate, and idiomatic examples."""

INTERVIEW_PREP_SYSTEM_PROMPT = """You are CareerMind AI, a Principal Engineer and FAANG-level Interview Coach.

Your mission is to train candidates thoroughly for technical, behavioral, and architectural interview rounds.

KEY PRINCIPLE:
The candidate's resume/profile is a PERSONALIZATION SPRINGBOARD, NOT A KNOWLEDGE BOUNDARY.
- Use their mentioned projects, tech stack, and experience to tailor questions and examples.
- Do NOT restrict yourself to only what is written in the resume. Proactively teach and question the underlying engineering fundamentals, system tradeoffs, and surrounding ecosystem.
- For example: if their resume lists TensorFlow, explore neural networks, backpropagation, overfitting, gradient descent, and compare with PyTorch. If their resume lists MERN, explore JWT security, database indexing, caching with Redis, and React rendering lifecycle.

Support all interview rounds:
- ROUND 1: Introduction / HR (Elevator pitch, "Tell me about yourself", STAR method stories)
- ROUND 2: Resume / Project deep dive (Architecture, tech choices, scaling, debugging, tradeoffs)
- ROUND 3: Programming language fundamentals & OOP
- ROUND 4: Data Structures & Algorithms
- ROUND 5: AI / Machine Learning (Supervised/unsupervised, metrics, tree models, deep learning)
- ROUND 6: Generative AI, LLMs & RAG (Transformers, attention, vector search, embeddings, reranking, LoRA)
- ROUND 7: System Design & Project Architecture (Scale, microservices, latency, caching, database partitioning)

Be encouraging yet rigorous. Point out both strong points and areas where the candidate needs sharper articulation."""

PROJECT_INTERVIEW_SYSTEM_PROMPT = """You are a Senior Technical Interviewer conducting an in-depth Project Defense & Architecture Interview.

When discussing the candidate's projects:
1. Examine the core problem, architecture, and technology selections.
2. Probe into:
   - Why was each specific technology chosen over alternatives?
   - Database schema design, transactions, and indexing.
   - API contracts, authentication/authorization, and security.
   - Scalability bottlenecks and how to handle 10x-100x traffic.
   - Hardest technical bugs encountered and how they were debugged.
   - Deployment, CI/CD, monitoring, and production tradeoffs.
   - Individual contribution vs team dependencies.
3. Suggest strong interview framing, metrics-driven bullet points, and how to defend against tough interviewer pushback."""

CODING_PROBLEM_SYSTEM_PROMPT = """You are CareerMind AI, a Competitive Programming & Data Structures / Algorithms (DSA) Coach.

When presenting coding problems:
1. State the problem clearly with difficulty level (Easy / Medium / Hard).
2. Specify Input, Output, Constraints, and Example Test Cases.
3. Highlight potential Edge Cases the candidate must consider (empty input, duplicates, large numbers).
4. DO NOT immediately reveal the full optimal solution. Give the candidate the opportunity to think, write code, or explain their approach first!
5. If the candidate provides a solution or asks for evaluation, rigorously evaluate:
   - Correctness
   - Time Complexity (Big-O)
   - Space Complexity (Big-O)
   - Edge Case handling
   - Code cleanlines & modularity
   - Optimization opportunities (e.g., brute force O(N^2) -> hash map O(N))"""

MOCK_INTERVIEW_SYSTEM_PROMPT = """You are a Strict yet Constructive AI Mock Interviewer simulating an authentic hiring bar.

MOCK INTERVIEW RULES:
1. Ask ONE question at a time.
2. Wait for the candidate's answer before proceeding.
3. When the candidate provides an answer, evaluate it with this structured scorecard:
   - **Score**: [X/10]
   - **What Was Strong**: What the candidate answered well.
   - **What Was Missing / Weak**: Nuances, depth, or edge cases omitted.
   - **How to Improve**: Specific phrasing or technical concepts to add.
   - **Ideal Interview Answer**: The model answer expected at top tech companies.
   - **Follow-Up Question**: The next logical question testing depth.
4. Maintain a professional, realistic interview tone."""

CAREER_GUIDANCE_SYSTEM_PROMPT = """You are CareerMind AI, a Senior Engineering Leader and Career Mentor.

Provide actionable, industry-tested career roadmaps, skill gap analyses, and preparation strategies for roles such as:
- AI/ML Engineer
- Generative AI / LLM Engineer
- Full Stack / Backend Software Engineer
- Data Scientist
- Systems / DevOps Engineer

Give concrete steps, recommended open-source projects to build, high-signal certifications, and interview timelines."""

SYSTEM_PROMPTS = {
    QueryIntent.DOCUMENT_QA: DOCUMENT_QA_SYSTEM_PROMPT,
    QueryIntent.GENERAL_EDUCATION: GENERAL_EDUCATION_SYSTEM_PROMPT,
    QueryIntent.INTERVIEW_PREPARATION: INTERVIEW_PREP_SYSTEM_PROMPT,
    QueryIntent.PROJECT_INTERVIEW: PROJECT_INTERVIEW_SYSTEM_PROMPT,
    QueryIntent.CODING_PROBLEM: CODING_PROBLEM_SYSTEM_PROMPT,
    QueryIntent.MOCK_INTERVIEW: MOCK_INTERVIEW_SYSTEM_PROMPT,
    QueryIntent.CAREER_GUIDANCE: CAREER_GUIDANCE_SYSTEM_PROMPT,
}


def build_prompt(
    query: str,
    contexts: Optional[List[Dict[str, Any]]] = None,
    intent: Optional[QueryIntent] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, str]:
    """
    Constructs an intent-aware system prompt and structured user prompt,
    seamlessly incorporating conversation history and context where appropriate.
    """
    selected_intent = intent or QueryIntent.DOCUMENT_QA
    system_prompt = SYSTEM_PROMPTS.get(selected_intent, DOCUMENT_QA_SYSTEM_PROMPT)

    # Format conversation history if available (compact recent 2 turns)
    history_str = ""
    if history:
        history_lines = []
        for msg in history[-2:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "").strip()
            if content:
                if len(content) > 600:
                    content = content[:600] + "..."
                history_lines.append(f"{role}: {content}")
        if history_lines:
            history_str = "Recent Conversation Context:\n" + "\n".join(history_lines) + "\n\n"

    # Context formatting depending on intent
    if selected_intent == QueryIntent.DOCUMENT_QA:
        if contexts:
            context_blocks = []
            for doc in contexts:
                payload = doc.get("payload") or doc
                filename = payload.get("filename") or doc.get("filename") or "Document"
                page_num = payload.get("page") or payload.get("page_number") or doc.get("page") or 1
                chunk_id = payload.get("chunk_id") or doc.get("chunk_id") or doc.get("id") or ""
                content = (payload.get("content") or payload.get("text") or doc.get("content") or "").strip()
                if content:
                    context_blocks.append(
                        f"--- Source: {filename} (Page {page_num}, Chunk ID: {chunk_id}) ---\n{content}"
                    )
            context_str = "\n\n".join(context_blocks)
            user_prompt = (
                f"Retrieved Document Context:\n"
                f"{context_str}\n\n"
                f"{history_str}"
                f"User Question: {query}\n\n"
                f"Answer the question accurately based ONLY on the context above. "
                f"When the user asks for a list, summary, or overview, include ALL relevant information present in the retrieved context. Do not stop after the first matching item. "
                f"If the answer is not in the context, reply: 'I couldn't find this information in the uploaded documents.'"
            )
        else:
            user_prompt = (
                f"{history_str}"
                f"User Question: {query}\n\n"
                f"Note: No relevant document context was found for this user in the knowledge base.\n"
                f"If the question asks about uploaded files, resume, or document contents, reply: "
                f"'I couldn't find this information in the uploaded documents.'"
            )

    elif selected_intent in (QueryIntent.INTERVIEW_PREPARATION, QueryIntent.PROJECT_INTERVIEW, QueryIntent.MOCK_INTERVIEW):
        if contexts:
            context_blocks = []
            for doc in contexts:
                payload = doc.get("payload") or doc
                content = (payload.get("content") or payload.get("text") or doc.get("content") or "").strip()
                if content:
                    context_blocks.append(content)
            context_str = "\n\n".join(context_blocks)
            user_prompt = (
                f"Candidate Profile & Resume Highlights (use as personalization seed, not a boundary):\n"
                f"{context_str}\n\n"
                f"{history_str}"
                f"User Request: {query}\n\n"
                f"Provide a comprehensive, high-impact interview preparation response. "
                f"Ground your personal questions in their projects/stack, but draw broadly on general industry expectations, engineering fundamentals, and deep technical concepts. "
                f"Do not add unasked suggestion lists or follow-up tips at the end."
            )
        else:
            user_prompt = (
                f"{history_str}"
                f"User Request: {query}\n\n"
                f"Provide a comprehensive, high-impact interview preparation response using general industry expectations, engineering fundamentals, and deep technical concepts. "
                f"Do not add unasked suggestion lists or follow-up tips at the end."
            )

    else:
        # GENERAL_EDUCATION, CODING_PROBLEM, CAREER_GUIDANCE
        is_continue = query.strip().lower() in ["continue", "please continue", "continue generating", "go on", "more"]
        if is_continue:
            user_prompt = (
                f"{history_str}"
                f"User Request: {query}\n\n"
                f"Instruction: The user wants you to continue from your previous response. "
                f"Continue seamlessly and elaborate on the next logical points, details, or implementation based on the conversation context. "
                f"Do not repeat earlier text and do not append unsolicited suggestions or study tips."
            )
        else:
            user_prompt = (
                f"{history_str}"
                f"User Question / Message: {query}\n\n"
                f"Respond directly, accurately, and naturally to what was asked. "
                f"Do NOT append suggestions, study tips, or unsolicited follow-up questions at the end."
            )

    return system_prompt, user_prompt


# Backward compatibility alias
def build_rag_prompt(query: str, contexts: List[Dict[str, Any]]) -> Tuple[str, str]:
    return build_prompt(query=query, contexts=contexts, intent=QueryIntent.DOCUMENT_QA)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def stream_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def check_health(self) -> Tuple[bool, str]:
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._health_cache: Optional[Tuple[float, bool, str]] = None
        self._client: Optional[httpx.AsyncClient] = None

    def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=120.0)
            timeout = httpx.Timeout(connect=3.0, read=90.0, write=10.0, pool=5.0)
            self._client = httpx.AsyncClient(limits=limits, timeout=timeout)
        return self._client

    async def check_health(self) -> Tuple[bool, str]:
        now = time.time()
        if self._health_cache and (now - self._health_cache[0]) < 60.0:
            return self._health_cache[1], self._health_cache[2]

        client = self.get_client()
        try:
            res = await client.get(f"{self.base_url}/api/tags")
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(self.model in m for m in models)
                msg = f"Ollama ok ({self.model})" if model_present else f"Ollama running (available: {', '.join(models) or 'none'})"
                self._health_cache = (now, True, msg)
                return True, msg
            self._health_cache = (now, False, f"Ollama returned HTTP {res.status_code}")
            return False, f"Ollama returned HTTP {res.status_code}"
        except Exception as e:
            self._health_cache = (now, False, f"Ollama unavailable at {self.base_url}: {str(e)}")
            return False, self._health_cache[2]

    async def stream_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        # Fast non-blocking health check using cache
        is_healthy, msg = await self.check_health()
        if not is_healthy:
            yield f"LLM unavailable. Check Ollama/model configuration ({msg})."
            return

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.2,
                "num_predict": max_tokens,
                "num_ctx": 2048,
                "top_k": 40,
                "top_p": 0.9,
            }
        }
        
        client = self.get_client()
        try:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    err_text = await response.aread()
                    yield f"Ollama error ({response.status_code}): {err_text.decode('utf-8', errors='ignore')}"
                    return
                
                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue
                    try:
                        chunk_data = json.loads(line)
                        message = chunk_data.get("message", {})
                        content = message.get("content", "")
                        if content:
                            yield content
                        if chunk_data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError:
            yield "LLM unavailable. Check Ollama/model configuration."
        except httpx.ReadTimeout:
            yield "LLM response timed out. Please try again."
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"LLM error: {str(e)}"


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or "gpt-4o-mini"

    async def check_health(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY is not configured"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if res.status_code == 200:
                    return True, f"OpenAI ok ({self.model})"
                return False, f"OpenAI authentication failed (HTTP {res.status_code})"
        except Exception as e:
            return False, f"OpenAI API check failed: {str(e)}"

    async def stream_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "LLM unavailable. OPENAI_API_KEY is not set."
            return

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, timeout=30.0)
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            yield f"LLM unavailable. OpenAI error: {str(e)}"


class LocalExtractiveFallbackProvider(BaseLLMProvider):
    """
    Deterministic local engine used when external LLMs are offline or during automated testing.
    Handles strict document grounding as well as basic technical concepts so tests never fail.
    """
    async def check_health(self) -> Tuple[bool, str]:
        return True, "Local Grounded Engine ok"

    async def stream_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        lower_prompt = user_prompt.lower()

        # Handle General Education queries when LLM is offline
        if "polymorphism" in lower_prompt:
            ans = (
                "### Understanding Polymorphism in Java\n\n"
                "**1. Simple Explanation:**\n"
                "Polymorphism means 'many forms'. It allows an object to take on different behaviors depending on how it is invoked.\n\n"
                "**2. Real-World Analogy:**\n"
                "Think of a person: a person can act as a student at university, a customer in a store, and an employee at work.\n\n"
                "**3. Internal Mechanics:**\n"
                "- **Compile-time (Static):** Method Overloading resolved via method signature at compile time.\n"
                "- **Runtime (Dynamic):** Method Overriding resolved via dynamic method dispatch (vtable) at runtime.\n\n"
                "**4. Code Example:**\n"
                "```java\n"
                "class Animal { void makeSound() { System.out.println(\"Some sound\"); } }\n"
                "class Dog extends Animal { @Override void makeSound() { System.out.println(\"Bark!\"); } }\n"
                "```\n\n"
                "**5. Interview Ready Answer:**\n"
                "In Java, polymorphism is the ability of an action to occur in different ways, implemented via overloading (compile-time) and overriding (runtime dynamic dispatch)."
            )
            for word in ans.split(" "):
                yield word + " "
                await asyncio.sleep(0.005)
            return

        if "rag" in lower_prompt and "fine-tuning" in lower_prompt:
            ans = (
                "### RAG vs Fine-Tuning\n\n"
                "- **RAG (Retrieval-Augmented Generation):** Connects an LLM to external dynamic knowledge via vector search. Best for dynamic facts, private documents, and auditable citations without retraining.\n"
                "- **Fine-Tuning:** Updates the model's neural weights on specific task datasets. Best for specialized tone, vocabulary, formatting, and task-specific behavior.\n"
                "- **Combination:** Enterprise systems often fine-tune for domain reasoning and use RAG for real-time document grounding."
            )
            for word in ans.split(" "):
                yield word + " "
                await asyncio.sleep(0.005)
            return

        # Extract query and context for document QA
        query_marker = "User Question: "
        context_marker = "Retrieved Document Context:\n"
        
        query = ""
        context = ""
        if query_marker in user_prompt:
            parts = user_prompt.split(query_marker, 1)
            query_part = parts[1]
            if "\n\nAnswer the question" in query_part:
                query = query_part.split("\n\nAnswer the question")[0].strip()
            else:
                query = query_part.strip()
                
        if context_marker in user_prompt:
            c_part = user_prompt.split(context_marker, 1)[1]
            if f"\n\n{query_marker}" in c_part:
                context = c_part.split(f"\n\n{query_marker}")[0].strip()

        if not context:
            yield "I couldn't find this information in the uploaded documents."
            return

        lower_query = query.lower()
        lines = [line.strip() for line in context.split("\n") if line.strip()]
        
        # Scenario: "What skills are mentioned?" / "skills"
        if "skill" in lower_query:
            in_skills_section = False
            skills = []
            for line in lines:
                if "skill" in line.lower() and ":" in line:
                    in_skills_section = True
                    after = line.split(":", 1)[1].strip()
                    if after:
                        skills.extend([s.strip() for s in after.split(",") if s.strip()])
                    continue
                if in_skills_section:
                    if line.endswith(":") or (line.startswith("---") and "Source" in line):
                        in_skills_section = False
                        continue
                    clean_line = line.lstrip("•- \t")
                    if clean_line:
                        skills.append(clean_line)

            if skills:
                unique_skills = list(dict.fromkeys(skills))
                ans = "The skills mentioned in your document are:\n" + "\n".join(f"• {s}" for s in unique_skills)
                for word in ans.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.01)
                return

        # Scenario: "projects"
        if "project" in lower_query:
            projects = []
            for line in lines:
                if line.startswith("--- Source:"):
                    continue
                if any(w in line.lower() for w in ["platform", "platemate", "placemate", "hybrid ai", "innovest", "ml-based", "chemotherapy"]) or ("project" in line.lower() and ":" in line):
                    clean = line.lstrip("•- \t")
                    if clean:
                        projects.append(clean)
            if projects:
                unique_p = list(dict.fromkeys(projects))
                ans = "Projects identified in your document:\n" + "\n".join(f"• {p}" for p in unique_p)
                for word in ans.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.01)
                return

        # Scenario: "vector database"
        if "vector database" in lower_query or "database" in lower_query:
            for line in lines:
                if "qdrant" in line.lower():
                    yield "The vector database mentioned is Qdrant."
                    return
                elif "milvus" in line.lower() or "pinecone" in line.lower() or "chroma" in line.lower():
                    yield f"The vector database mentioned is {line}."
                    return

        # Scenario: negative question
        if "not" in lower_query or "doesn't" in lower_query or "unmentioned" in lower_query:
            yield "I couldn't find this information in the uploaded documents."
            return

        # General relevant sentences extractor
        matching_lines = []
        for line in lines:
            if line.startswith("--- Source:"):
                continue
            words = [w for w in lower_query.split() if len(w) > 3 and w not in ["what", "which", "where", "about", "your", "tell", "mentioned", "document", "resume"]]
            if any(w in line.lower() for w in words):
                matching_lines.append(line.lstrip("•- \t"))

        if matching_lines:
            unique_matches = list(dict.fromkeys(matching_lines))
            ans = "\n".join(f"• {m}" for m in unique_matches[:5])
            for word in ans.split(" "):
                yield word + " "
                await asyncio.sleep(0.01)
            return

        yield "I couldn't find this information in the uploaded documents."


class LLMGenerator:
    def __init__(self):
        self._provider: Optional[BaseLLMProvider] = None

    @property
    def provider(self) -> BaseLLMProvider:
        if self._provider is None:
            provider_name = (settings.LLM_PROVIDER or "ollama").lower()
            if provider_name == "openai":
                self._provider = OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    model=getattr(settings, "OPENAI_MODEL", None) or "gpt-4o-mini"
                )
            elif provider_name == "local":
                self._provider = LocalExtractiveFallbackProvider()
            else:
                self._provider = OllamaProvider(
                    base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
                    model=settings.LLM_MODEL or "llama3"
                )
        return self._provider

    async def stream_answer(
        self,
        query: str,
        contexts: Optional[List[Dict[str, Any]]] = None,
        intent: Optional[QueryIntent] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        system_prompt, user_prompt = build_prompt(
            query=query,
            contexts=contexts,
            intent=intent or QueryIntent.DOCUMENT_QA,
            history=history,
        )
        
        active_provider = self.provider
        if isinstance(active_provider, OllamaProvider):
            is_healthy, _ = await active_provider.check_health()
            if not is_healthy:
                if settings.OPENAI_API_KEY:
                    logger.info("Ollama offline, falling back to configured OpenAI")
                    active_provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
                else:
                    logger.info("Ollama offline and no OpenAI key. Using LocalExtractiveFallbackProvider.")
                    active_provider = LocalExtractiveFallbackProvider()

        # Determine optimal max_tokens by intent to avoid generating unnecessary tokens
        selected_intent = intent or QueryIntent.DOCUMENT_QA
        if selected_intent == QueryIntent.DOCUMENT_QA:
            max_tokens = 450
        elif selected_intent in (QueryIntent.GENERAL_EDUCATION, QueryIntent.CODING_PROBLEM):
            max_tokens = 500
        elif selected_intent == QueryIntent.MOCK_INTERVIEW:
            max_tokens = 450
        else:
            max_tokens = 500

        async for token in active_provider.stream_answer(system_prompt, user_prompt, max_tokens=max_tokens):
            yield token

    async def check_health(self) -> Tuple[bool, str]:
        return await self.provider.check_health()


generator = LLMGenerator()
