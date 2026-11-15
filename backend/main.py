from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

from .config import DATABASE_PATH
from .db import RunStore
from .llm import OllamaLessonLLM
from .schemas import LessonRequest, LessonResult, RunSummary
from .service import LessonService

app = FastAPI(
    title="Self-Evaluating Lesson Generator API",
    summary="Generate, evaluate, and persist locally generated lessons.",
    description="""This API uses a local Ollama model through LangChain and a LangGraph workflow.

Every draft is checked against a strict structured rubric. Failed drafts receive evaluator feedback and can be regenerated up to two times, for a maximum of three drafts. SQLite preserves completed runs and every rejected draft for auditing.""",
    version="1.0.0",
    contact={"name": "Lesson Generator"},
)
store = RunStore(DATABASE_PATH)
service = LessonService(OllamaLessonLLM(), store)


@app.get("/health", tags=["System"], summary="Check service availability", description="Returns once the FastAPI process is running. It does not make a model call.")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/lessons",
    response_model=LessonResult,
    tags=["Lessons"],
    summary="Generate and self-evaluate a lesson",
    description="Creates a lesson for the requested learner, evaluates it, and regenerates rejected drafts up to two times. Set `inject_error` to test the rejection-and-retry path.",
    responses={503: {"description": "Ollama is unavailable or the model returned invalid structured output."}},
)
def create_lesson(request: LessonRequest) -> LessonResult:
    try:
        return service.create_lesson(request)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Local model unavailable or returned invalid output: {error}") from error


@app.get(
    "/runs",
    response_model=list[RunSummary],
    tags=["Runs"],
    summary="List recent generation runs",
    description="Returns the 20 most recent persistent run summaries, newest first.",
)
def runs() -> list[RunSummary]:
    return store.recent_runs()


@app.get(
    "/runs/{run_id}", response_model=LessonResult, tags=["Runs"], summary="Get a saved lesson run",
    description="Returns the full lesson and final evaluator result for a selected persistent run.",
    responses={404: {"description": "No saved run exists for this ID."}},
)
def run_detail(run_id: int) -> LessonResult:
    result = store.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result
