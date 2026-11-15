import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .schemas import LessonResult, RubricResult, RunSummary


class RunStore:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            # `lesson_runs` contains final outcomes; `rejection_logs` preserves failed attempts.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS lesson_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL, audience TEXT NOT NULL, duration_minutes INTEGER NOT NULL,
                    status TEXT NOT NULL, attempts INTEGER NOT NULL, lesson TEXT NOT NULL,
                    evaluation_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS rejection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL, attempt INTEGER NOT NULL, lesson TEXT NOT NULL,
                    evaluation_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES lesson_runs(id)
                )
            """)

    def save_run(self, topic: str, audience: str, duration: int, result: LessonResult) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO lesson_runs(topic,audience,duration_minutes,status,attempts,lesson,evaluation_json) VALUES(?,?,?,?,?,?,?)",
                (topic, audience, duration, result.status, result.attempts, result.lesson, result.evaluation.model_dump_json()),
            )
            return int(cursor.lastrowid)

    def save_rejection(self, run_id: int, attempt: int, lesson: str, evaluation_json: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO rejection_logs(run_id,attempt,lesson,evaluation_json) VALUES(?,?,?,?)",
                (run_id, attempt, lesson, evaluation_json),
            )

    def recent_runs(self, limit: int = 20) -> list[RunSummary]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT id, topic, status, attempts, created_at FROM lesson_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RunSummary(**dict(row)) for row in rows]

    def get_run(self, run_id: int) -> LessonResult | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT id, status, attempts, lesson, evaluation_json FROM lesson_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return LessonResult(
            run_id=row["id"],
            status=row["status"],
            attempts=row["attempts"],
            lesson=row["lesson"],
            evaluation=RubricResult.model_validate(json.loads(row["evaluation_json"])),
        )

    def rejection_count(self) -> int:
        with self.connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM rejection_logs").fetchone()[0])
