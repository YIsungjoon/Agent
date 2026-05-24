from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

class IRAC(BaseModel):
    issue: str = ""
    rule: str = ""
    application: str = ""
    conclusion: str = ""

    @field_validator("issue", "rule", "application", "conclusion", mode="before")
    @classmethod
    def convert_list_to_string(cls, v: Any) -> str:
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        if v is None:
            return ""
        return str(v)

class IRACNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    parent_id: Optional[str] = None
    depth: int = 0
    agent_type: Optional[str] = None
    owner_agent: Optional[str] = None
    status: str = "draft"
    irac: IRAC = Field(default_factory=IRAC)
    confidence: float = 1.0
    evidence: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    open_edges: List[Dict[str, Any]] = Field(default_factory=list)
    tool_intents: List[str] = Field(default_factory=list)
    tool_observations: List[str] = Field(default_factory=list)

    @field_validator("evidence", "unknowns", "tool_intents", "tool_observations", mode="before")
    @classmethod
    def convert_string_to_list(cls, v: Any) -> list:
        if isinstance(v, str):
            return [v] if v.strip() else []
        if v is None:
            return []
        if isinstance(v, list):
            return [str(item) for item in v]
        return [str(v)]


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    # 'from' is a reserved keyword in Python, so we alias it
    from_node: str = Field(..., alias="from")
    to: str
    type: str
    reason: Optional[str] = None

class SharedEntry(BaseModel):
    id: str
    kind: str
    node_id: Optional[str] = None
    text: str
    confidence: float = 1.0

class ToolIntent(BaseModel):
    id: str
    node_id: str
    agent_id: str
    tool_name: str
    tool_group: Optional[str] = None
    risk: str = "low"
    purpose: str
    expected_output: str
    preflight: Optional[str] = None
    approval_status: Optional[str] = "pending"
    provenance_policy: Optional[str] = None
    fallback: Optional[str] = None

class ToolObservation(BaseModel):
    id: str
    intent_id: str
    node_id: str
    observation_type: str = "observation"
    provenance: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    content: str
    extracted_claims: List[Dict[str, Any]] = Field(default_factory=list)

class Workspace(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    run_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    question: str
    max_depth: int = 2
    status: str = "open"
    answer_draft: Optional[str] = None
    used_langgraph: bool = True
    model_note: Optional[str] = None
    
    nodes: List[IRACNode] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    shared_entries: List[SharedEntry] = Field(default_factory=list)
    source_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    agent_roster: List[Dict[str, Any]] = Field(default_factory=list)
    agent_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    handoffs: List[Dict[str, Any]] = Field(default_factory=list)
    agent_events: List[Dict[str, Any]] = Field(default_factory=list)
    tool_intents: List[ToolIntent] = Field(default_factory=list)
    tool_observations: List[ToolObservation] = Field(default_factory=list)
    memory_candidates: List[Dict[str, Any]] = Field(default_factory=list)
