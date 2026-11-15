from backend.db import RunStore
from backend.graph import build_graph
from backend.schemas import LessonRequest, RubricResult
from backend.service import LessonService


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, request, feedback=""):
        self.calls += 1
        if self.calls == 1:
            return "# Learning objectives\n- Learn\n# Explanation\nText\n# Example\nOne\n# Practice exercise\nDo it\n# Answers\nAnswer"
        return "# Learning objectives\n- Learn\n# Explanation\nText\n# Example\nOne\n# Practice exercise\nDo it\n# Answer key\nAnswer"

    def evaluate(self, request, lesson):
        passed = "# Answer key" in lesson
        return RubricResult(passed=passed, score=100 if passed else 30, missing_requirements=[] if passed else ["Answer key"], feedback="Add Answer key" if not passed else "Meets rubric")


def test_retries_after_failed_validation_and_persists_results(tmp_path):
    store = RunStore(tmp_path / "runs.db")
    service = LessonService(FakeLLM(), store)
    result = service.create_lesson(LessonRequest(topic="fractions"))
    assert result.status == "passed"
    assert result.attempts == 2
    assert result.run_id == 1
    assert store.recent_runs()[0].status == "passed"
    assert store.rejection_count() == 1
    saved_run = store.get_run(result.run_id)
    assert saved_run is not None
    assert saved_run.lesson == result.lesson


def test_retried_run_includes_final_evaluation_in_graph_state():
    state = build_graph(FakeLLM()).invoke(
        {"request": LessonRequest(topic="fractions"), "attempts": 0, "feedback": "", "rejections": []}
    )
    assert state["attempts"] == 2
    assert state["final_evaluation"] == {
        "passed": True,
        "score": 100,
        "missing_requirements": [],
        "feedback": "Meets rubric",
    }


def test_failure_is_bounded_at_three_attempts(tmp_path):
    class AlwaysFail(FakeLLM):
        def evaluate(self, request, lesson):
            return RubricResult(passed=False, score=0, missing_requirements=["quality"], feedback="Try again")
    store = RunStore(tmp_path / "runs.db")
    result = LessonService(AlwaysFail(), store).create_lesson(LessonRequest(topic="fractions"))
    assert result.status == "failed"
    assert result.attempts == 3
    assert store.rejection_count() == 3
