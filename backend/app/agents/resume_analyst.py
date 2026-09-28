from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from app.agents.base_agent import get_agent_llm

class ResumeAnalystAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_agent_llm(temperature=0.1)
        return self._llm

    async def analyze_resume(self, resume_text: str) -> str:
        if not self.llm:
            return "Resume Analyst Agent is currently unavailable. Please configure Ollama or OpenAI."
            
        prompt = PromptTemplate(
            input_variables=["resume"],
            template=(
                "You are an expert AI recruiter and resume analyst.\n"
                "Extract the following information from the provided resume:\n"
                "- Core Skills (categorized by language, framework, tool)\n"
                "- Total Years of Experience\n"
                "- Key Projects and their technical stack\n"
                "- Strengths and Weaknesses\n\n"
                "Resume:\n{resume}\n\n"
                "Return the output in clear, structured Markdown."
            )
        )
        
        formatted_prompt = prompt.format(resume=resume_text)
        response = await self.llm.ainvoke(formatted_prompt)
        return response.content

resume_analyst = ResumeAnalystAgent()
