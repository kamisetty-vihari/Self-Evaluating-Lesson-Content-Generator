from typing import Literal
from pydantic import BaseModel, Field


class LessonRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    audience: str = Field(default="beginner", min_length=2, max_length=100)
    duration_minutes: int = Field(default=20, ge=5, le=180)


class RubricResult(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    missing_requirements: list[str] = Field(default_factory=list)
    feedback: str


class LessonResult(BaseModel):
    run_id: int
    status: Literal["passed", "failed"]
    attempts: int
    lesson: str
    evaluation: RubricResult


class RunSummary(BaseModel):
    id: int
    topic: str
    status: str
    attempts: int
    created_at: str
