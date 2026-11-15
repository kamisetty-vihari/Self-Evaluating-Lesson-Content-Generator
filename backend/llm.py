import json

from .config import OLLAMA_HOST, OLLAMA_MODEL
from .schemas import LessonRequest, RubricResult


class OllamaLessonLLM:
    def __init__(self, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        try:
            from langchain_ollama import ChatOllama
        except ImportError as error:
            raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from error
        self.client = ChatOllama(model=model, base_url=host, temperature=0)

    def generate(self, request: LessonRequest, feedback: str = "") -> str:
        correction = f"Previous evaluator feedback: {feedback}" if feedback else ""
        prompt = f"""Create a {request.duration_minutes}-minute lesson about {request.topic} for a {request.audience} learner.
Return markdown containing exactly these sections: Learning objectives, Explanation, Example, Practice exercise, Answer key.
Make objectives measurable and give a correct, self-contained answer key. {correction}"""
        response = self.client.invoke(prompt)
        return str(response.content)

    def evaluate(self, request: LessonRequest, lesson: str) -> RubricResult:
        prompt = f"""You are a strict lesson-quality evaluator. Evaluate this lesson about {request.topic}.
Pass only if it has all required sections (Learning objectives, Explanation, Example, Practice exercise, Answer key), is appropriate for {request.audience}, and the answer key answers the exercise.
Return JSON only: {{"passed": boolean, "score": 0-100, "missing_requirements": [string], "feedback": string}}.
LESSON:\n{lesson}"""
        response = self.client.bind(format="json").invoke(prompt)
        return RubricResult.model_validate(json.loads(str(response.content)))
