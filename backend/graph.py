from typing import TypedDict
from langgraph.graph import END, StateGraph

from .config import MAX_RETRIES
from .schemas import LessonRequest, RubricResult


class LessonState(TypedDict, total=False):
    request: LessonRequest
    lesson: str
    evaluation: RubricResult
    attempts: int
    feedback: str
    rejections: list[tuple[int, str, RubricResult]]
    final_evaluation: dict[str, object]


def build_graph(llm):
    def generate(state: LessonState) -> LessonState:
        lesson = llm.generate(state["request"], state.get("feedback", ""))
        return {"lesson": lesson, "attempts": state.get("attempts", 0) + 1}

    def evaluate(state: LessonState) -> LessonState:
        evaluation = llm.evaluate(state["request"], state["lesson"])
        rejections = list(state.get("rejections", []))
        if not evaluation.passed:
            # Keep every rejected draft so the service can persist an audit trail.
            rejections.append((state["attempts"], state["lesson"], evaluation))
        return {"evaluation": evaluation, "feedback": evaluation.feedback, "rejections": rejections}

    def route(state: LessonState) -> str:
        if state["evaluation"].passed:
            return "finalize"
        # `attempts` includes the initial draft; MAX_RETRIES therefore allows three drafts total.
        return "retry" if state["attempts"] <= MAX_RETRIES else "finalize"

    def finalize(state: LessonState) -> LessonState:
        # A plain dictionary makes the final rubric result easy to inspect in LangSmith.
        return {"final_evaluation": state["evaluation"].model_dump()}

    graph = StateGraph(LessonState)
    graph.add_node("generate", generate)
    graph.add_node("evaluate", evaluate)
    graph.add_node("finalize", finalize)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "evaluate")
    graph.add_conditional_edges("evaluate", route, {"retry": "generate", "finalize": "finalize"})
    graph.add_edge("finalize", END)
    return graph.compile()
