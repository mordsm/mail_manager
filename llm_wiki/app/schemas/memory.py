from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

class CaptureEvent(BaseModel):
    event_id: Optional[str] = None
    source_type: str = Field(..., description="browser, llm_chat, dev, terminal, manual")
    domain: str = "unclassified"
    title: str
    url_or_path: Optional[str] = None
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    time_spent_seconds: int = 0
    project_hint: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationCapture(BaseModel):
    conversation_id: str
    model: str = "llm"
    url: Optional[str] = None
    project_hint: Optional[str] = None
    messages_count: int = 0
    decisions: List[str] = Field(default_factory=list)
    key_facts: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    raw_content: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class DevelopmentCapture(BaseModel):
    project: str
    action: str = "code_change"
    changed_files: List[str] = Field(default_factory=list)
    commit_msg: Optional[str] = None
    reason: Optional[str] = None
    test_status: Optional[str] = "passed"
    next_steps: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class SessionRecord(BaseModel):
    session_id: str
    session_type: Literal["research", "development", "browsing", "llm_dialogue"]
    title: str
    domain: str
    project: Optional[str] = None
    start_time: str
    end_time: str
    importance_score: float = 50.0
    events_count: int = 0
    sources_reviewed: List[str] = Field(default_factory=list)
    summary: str = ""
    decisions: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)

class DecisionRecord(BaseModel):
    decision_id: str
    project_or_domain: str
    topic: str
    decision: str
    reason: str
    previous_state: Optional[str] = None
    open_questions: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ProjectMemoryState(BaseModel):
    project_name: str
    goal: str = ""
    current_state: str = ""
    architecture_overview: str = ""
    important_files: List[str] = Field(default_factory=list)
    recent_work: List[str] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    completed_features: List[str] = Field(default_factory=list)
    open_issues: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
