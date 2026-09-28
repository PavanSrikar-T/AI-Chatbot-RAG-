from langchain_core.prompts import PromptTemplate
from app.agents.base_agent import get_agent_llm

class InterviewAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_agent_llm(temperature=0.7)
        return self._llm

    async def generate_questions(self, job_analysis: str, resume_analysis: str) -> str:
        if not self.llm:
            return "Interview Agent is currently unavailable. Please configure Ollama or OpenAI."
            
        prompt = PromptTemplate(
            input_variables=["job", "resume"],
            template=(
                "You are an expert technical interviewer.\n"
                "Based on the following Job Analysis and Resume Analysis, generate 5 highly relevant interview questions.\n"
                "Mix technical questions, system design (if applicable), and behavioral questions.\n"
                "Tailor the questions specifically to probe the candidate's stated experience and the job's requirements.\n\n"
                "Job Analysis:\n{job}\n\n"
                "Resume Analysis:\n{resume}\n\n"
                "Return a JSON list of questions."
            )
        )
        
        formatted_prompt = prompt.format(job=job_analysis, resume=resume_analysis)
        response = await self.llm.ainvoke(formatted_prompt)
        return response.content

    async def evaluate_answer(self, question: str, answer: str) -> str:
        if not self.llm:
            return "Interview Agent is currently unavailable. Please configure Ollama or OpenAI."
            
        prompt = PromptTemplate(
            input_variables=["question", "answer"],
            template=(
                "You are an expert technical interviewer evaluating a candidate's answer.\n"
                "Question: {question}\n"
                "Candidate's Answer: {answer}\n\n"
                "Evaluate the answer based on:\n"
                "- Technical Correctness\n"
                "- Clarity\n"
                "- Completeness\n"
                "Provide constructive feedback and a score out of 10."
            )
        )
        
        formatted_prompt = prompt.format(question=question, answer=answer)
        response = await self.llm.ainvoke(formatted_prompt)
        return response.content

interview_agent = InterviewAgent()
