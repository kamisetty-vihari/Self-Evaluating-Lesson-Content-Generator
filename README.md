# Self-Evaluating Lesson Generator

Generates a lesson through local Ollama using LangChain's `ChatOllama`, evaluates it against a strict structured rubric, and regenerates it at most twice (three total drafts). FastAPI exposes the backend and Streamlit calls it over REST. SQLite stores every run plus rejected drafts for auditability.

## Model choice

Default: `qwen2.5:7b`. It is a strong instruction-following model for a 16 GB Windows machine with a dedicated GPU. For lower available VRAM, use `qwen2.5:3b`; for 12 GB+ VRAM, `qwen2.5:14b` can improve lesson quality at a latency cost. Set `OLLAMA_MODEL` in `.env` to override the default.

## Windows setup

1. Install [Ollama for Windows](https://ollama.com/download) and then, in PowerShell, run `ollama pull qwen2.5:3b`.
2. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Start the backend in one terminal:
   ```powershell
   uvicorn backend.main:app --reload
   ```
4. Start the frontend in another:
   ```powershell
   streamlit run frontend/streamlit_app.py
   ```

Open `http://127.0.0.1:8501`. The API documentation is at `http://127.0.0.1:8000/docs`.

## LangSmith observability

LangSmith traces the LangChain `ChatOllama` calls made during lesson generation and evaluation. The application reads standard LangSmith environment variables; it never stores an API key in source code.

1. Revoke the API key that was posted in chat and create a replacement in LangSmith.
2. Copy `.env.example` to `.env`, then replace `replace-with-a-new-key` with the replacement key.
3. Start the backend normally. It automatically loads `.env` at startup:
   ```powershell
   uvicorn backend.main:app --reload
   ```

Open your LangSmith project, `self-evaluating-lesson-generator`, to inspect generation and evaluation traces. Tracing is disabled unless `LANGSMITH_TRACING=true` and a valid `LANGSMITH_API_KEY` are set.

## API

`POST /lessons` accepts `topic`, `audience`, and `duration_minutes`. `GET /runs` returns persistent run summaries; `GET /runs/{run_id}` returns the selected lesson's complete output. Streamlit refreshes history automatically after every page rerun, including after a new lesson is generated; use **View lesson output** for a specific run.

Streamlit disables lesson submission while generation is in progress and waits up to 10 minutes for a local model response.

## Tests

```powershell
pytest -q
```

The backend retry test is `backend/tests/test_service.py::test_retries_after_failed_validation_and_persists_results`. It simulates an evaluator rejecting the first draft, verifies that the graph generates a corrected second draft, and checks the rejected draft is logged.

Run only that test:

```powershell
pytest backend/tests/test_service.py::test_retries_after_failed_validation_and_persists_results -q
```
