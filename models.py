"""Pydantic models for the Bug Triage OpenEnv environment."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ── Issue data models ──────────────────────────────────────────────────────────

class IssueReport(BaseModel):
    """A software issue submitted by a user."""
    id: str
    title: str
    description: str
    reporter: str
    created_at: str
    component: str
    reproduction_steps: Optional[str] = None
    environment_info: Optional[str] = None


class BacklogIssue(BaseModel):
    """An existing issue in the backlog (with known metadata)."""
    id: str
    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low"]
    labels: List[str]
    status: str
    component: str


# ── OpenEnv core models ────────────────────────────────────────────────────────

class TriageState(BaseModel):
    """Tracks what the agent has done so far in the episode."""
    task: str = ""
    scenario_id: int = 0
    classified: bool = False
    severity_assigned: Optional[str] = None
    duplicates_marked: List[str] = Field(default_factory=list)
    response_drafted: bool = False
    response_text: Optional[str] = None
    labels_assigned: List[str] = Field(default_factory=list)
    submitted: bool = False
    cumulative_reward: float = 0.0
    step: int = 0
    max_steps: int = 5
    done: bool = False


class Observation(BaseModel):
    """What the agent sees each step."""
    task: str
    instructions: str
    current_issue: IssueReport
    backlog: List[BacklogIssue]
    step: int
    max_steps: int
    triage_state: TriageState
    available_actions: List[str]
    available_labels: List[str]
    last_action_feedback: str = ""


class Action(BaseModel):
    """What the agent can do."""
    action_type: Literal["classify", "mark_duplicate", "draft_response", "assign_labels", "submit"]
    # For classify
    severity: Optional[Literal["critical", "high", "medium", "low"]] = None
    # For mark_duplicate
    duplicate_of: Optional[str] = None
    # For draft_response
    response_text: Optional[str] = None
    # For assign_labels
    labels: Optional[List[str]] = None


class StepResult(BaseModel):
    """Return value of env.step()."""
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any]


class ResetResult(BaseModel):
    """Return value of env.reset()."""
    observation: Observation
    info: Dict[str, Any]


class StateResult(BaseModel):
    """Return value of env.state()."""
    state: TriageState
    info: Dict[str, Any]


# ── Request models ─────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task: Literal["bug_classify", "duplicate_detection", "full_triage"] = "bug_classify"
    scenario_id: Optional[int] = None  # None = random
    seed: Optional[int] = None
