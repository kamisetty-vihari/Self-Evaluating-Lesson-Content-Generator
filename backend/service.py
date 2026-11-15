from .db import RunStore
from .graph import build_graph
from .schemas import LessonRequest, LessonResult


class LessonService:
    def __init__(self, llm, store: RunStore):
        self.llm = llm
        self.store = store
    def create_lesson(self, request: LessonRequest) -> LessonResult:
        graph = build_graph(self.llm)
        state = graph.invoke({"request": request, "attempts": 0, "feedback": "", "rejections": []})
        result = LessonResult(
            run_id=0,
            status="passed" if state["evaluation"].passed else "failed",
            attempts=state["attempts"], lesson=state["lesson"], evaluation=state["evaluation"],
        )
        # Save the final outcome first so rejected drafts can reference its run ID.
        run_id = self.store.save_run(request.topic, request.audience, request.duration_minutes, result)
        for attempt, lesson, evaluation in state["rejections"]:
            self.store.save_rejection(run_id, attempt, lesson, evaluation.model_dump_json())
        return result.model_copy(update={"run_id": run_id})
