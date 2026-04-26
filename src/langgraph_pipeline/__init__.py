"""
VJH LangGraph Pipeline
Stateful, checkpointed job processing graph replacing the raw for-loop in orchestrator.py.

Key exports:
  VJHLangGraphRunner  — batch processor + human-approval resume
  JobState            — TypedDict for per-job state
  build_graph         — compile the StateGraph (for testing)
"""

from .runner import VJHLangGraphRunner
from .state import JobState
from .pipeline import build_graph

__all__ = ["VJHLangGraphRunner", "JobState", "build_graph"]
