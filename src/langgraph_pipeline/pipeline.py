"""
VJH LangGraph Pipeline Definition
Builds the StateGraph and compiles it with an AsyncSqliteSaver checkpointer.

Graph topology:
    START
      └─→ gate_node
            ├─→ (gated out) discard_node → notify_node → END
            └─→ score_node
                  └─→ route_node
                        ├─→ (score ≥70) ──────────────────────────────┐
                        ├─→ (score 60-69) interrupt_before ──────────→ submit_node → notify_node → END
                        ├─→ (score 55-59) outreach_node → notify_node → END
                        └─→ (score <55)  discard_node  → notify_node → END

Checkpointing: every node write is checkpointed to SQLite.
Thread ID = vjh_{job_id} — stable across hourly cycles.
Deduplication: runner checks checkpoint before invoking; skips completed threads.
Human-in-the-loop: interrupt_before=["submit_node"] for human_review route.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .state import JobState
from .nodes import (
    gate_node,
    score_node,
    route_node,
    submit_node,
    outreach_node,
    discard_node,
    notify_node,
    should_continue_after_gate,
    route_after_score,
)


def build_graph(checkpointer: AsyncSqliteSaver) -> any:
    """
    Build and compile the VJH LangGraph StateGraph.

    interrupt_before=["submit_node"] means:
      - Jobs with route="human_review" (score 60-69) pause here.
      - Elena gets a Telegram message asking for approval.
      - When she sends /approve_vjh_{job_id}, the runner resumes the thread.
      - If she sends /reject_vjh_{job_id}, the runner updates human_approved=False and resumes
        (submit_node checks this and skips the application).
    """
    builder = StateGraph(JobState)

    # Register nodes
    builder.add_node("gate_node",     gate_node)
    builder.add_node("score_node",    score_node)
    builder.add_node("route_node",    route_node)
    builder.add_node("submit_node",   submit_node)
    builder.add_node("outreach_node", outreach_node)
    builder.add_node("discard_node",  discard_node)
    builder.add_node("notify_node",   notify_node)

    # Entry point
    builder.add_edge(START, "gate_node")

    # After gate: pass → score, fail → discard
    builder.add_conditional_edges("gate_node", should_continue_after_gate, {
        "score_node":   "score_node",
        "discard_node": "discard_node",
    })

    # Scoring always leads to routing
    builder.add_edge("score_node", "route_node")

    # After route: branch to submit / outreach / discard
    builder.add_conditional_edges("route_node", route_after_score, {
        "submit_node":   "submit_node",
        "outreach_node": "outreach_node",
        "discard_node":  "discard_node",
    })

    # Terminal paths all lead to notify, then END
    builder.add_edge("submit_node",   "notify_node")
    builder.add_edge("outreach_node", "notify_node")
    builder.add_edge("discard_node",  "notify_node")
    builder.add_edge("notify_node",   END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["submit_node"],  # Pause here for human_review route
    )
