from typing import List, Literal, Dict
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.documents import Document


# --------------------------------
# ROUTING DECISION
# --------------------------------

class RouteDecision(BaseModel):

    route: Literal["kb", "direct"] = Field(
        description="kb for IT/support questions; direct for greetings/simple chat"
    )


# --------------------------------
# EVIDENCE GRADING
# --------------------------------

class EvidenceGrade(BaseModel):

    grade: Literal["good", "weak"] = Field(
        description="Whether evidence is sufficient to answer"
    )


# --------------------------------
# LANGGRAPH AGENT STATE
# --------------------------------

class AgentState(TypedDict):

    question: str
    current_query: str

    # Knowledge Base
    kb_docs: List[Document]
    kb_grade: Literal["", "good", "weak"]

    # Web Search
    web_results: str
    web_grade: Literal["", "good", "weak"]

    # Response
    answer: str
    source_used: str

    # Retry Management
    retry_count: int

    # Tracking
    trace: List[str]

    # Citations
    citations: List[Dict[str, str]]