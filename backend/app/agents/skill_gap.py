from langchain_core.prompts import PromptTemplate
from app.agents.base_agent import get_agent_llm

class SkillGapAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_agent_llm(temperature=0.1)
        return self._llm

    async def analyze_gap(self, resume_analysis: str, job_analysis: str) -> str:
        if not self.llm:
            return "Skill Gap Agent is currently unavailable. Please configure Ollama or OpenAI."
            
        prompt = PromptTemplate(
            input_variables=["resume", "job"],
            template=(
                "You are an expert career counselor and technical evaluator.\n"
                "Compare the candidate's Resume Analysis with the Job Analysis.\n"
                "Provide:\n"
                "1. Skill Overlap (matching skills)\n"
                "2. Missing Skills (skill gaps)\n"
                "3. Match Score (0-100% with justification)\n"
                "4. A 14-day study/preparation plan to bridge the gaps.\n\n"
                "Resume Analysis:\n{resume}\n\n"
                "Job Analysis:\n{job}\n\n"
                "Output as structured Markdown."
            )
        )
        
        formatted_prompt = prompt.format(resume=resume_analysis, job=job_analysis)
        response = await self.llm.ainvoke(formatted_prompt)
        return response.content

skill_gap_agent = SkillGapAgent()
