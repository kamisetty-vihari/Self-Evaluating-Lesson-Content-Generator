from pathlib import Path
import os

# All runtime values can be changed in `.env` without editing source code.
DATABASE_PATH = Path(os.getenv("LESSON_DB_PATH", "data/lesson_runs.db"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
# One initial draft plus two corrections prevents an unbounded retry loop.
MAX_RETRIES = 2
