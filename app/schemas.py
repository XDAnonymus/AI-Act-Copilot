from typing import Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


Intent = Literal[
    "general_research",
    "scope_check",
    "risk_assessment",
    "obligation_check",
    "timeline_question",
    "prohibited_practice_check",
    "out_of_scope",
]


class AgentDecision(BaseModel):
    in_scope: bool
    intent: Intent
    research_tasks: list[str] = Field(default_factory=list, max_length=4)
    needs_risk_tool: bool = False
    needs_date_tool: bool = False
    reason: str = ""


class AgentState(TypedDict, total=False):
    question: str
    as_of: str
    intent: str
    decision: dict
    research_tasks: list[str]
    evidence: list[dict]
    tool_results: list[dict]
    draft_answer: str
    verification: dict
    final_answer: str
    retry_count: int
    trace: list[dict]


class RAGState(TypedDict, total=False):
    query: str
    top_k: int
    hits: list[dict]
    evidence: list[dict]
