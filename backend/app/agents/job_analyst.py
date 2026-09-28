from langchain_core.prompts import PromptTemplate
from app.agents.base_agent import get_agent_llm

class JobAnalystAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_agent_llm(temperature=0.1)
        return self._llm

    async def analyze_job(self, job_description: str) -> str:
        if not self.llm:
            return "Job Analyst Agent is currently unavailable. Please configure Ollama or OpenAI."
            
        prompt = PromptTemplate(
            input_variables=["job"],
            template=(
                "You are an expert technical recruiter.\n"
                "Analyze the following job description and extract:\n"
                "- Required Skills\n"
                "- Preferred/Nice-to-have Skills\n"
                "- Experience Requirements\n"
                "- Core Technologies & Frameworks\n"
                "- Main Responsibilities\n\n"
                "Job Description:\n{job}\n\n"
                "Provide the response as a structured JSON object or clear Markdown list."
            )
        )
        
        formatted_prompt = prompt.format(job=job_description)
        response = await self.llm.ainvoke(formatted_prompt)
        return response.content

job_analyst = JobAnalystAgent()
