"""
FastAPI server for the Bug Triage OpenEnv environment.
Exposes: POST /reset, POST /step, GET /state

Session isolation: each caller passes an optional `session_id` header.
Falls back to a shared default session for backwards compatibility.
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional

from environment import BugTriageEnv
from models import (
    Action,
    ResetRequest,
    ResetResult,
    StateResult,
    StepResult,
)

app = FastAPI(
    title="Bug Triage OpenEnv",
    description=(
        "OpenEnv environment for AI-driven software bug triage. "
        "Tasks: bug_classify (easy), duplicate_detection (medium), full_triage (hard)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session-keyed env store — prevents concurrent callers from clobbering each other
_envs: Dict[str, BugTriageEnv] = {}
DEFAULT_SESSION = "default"


def _get_env(session_id: str) -> BugTriageEnv:
    if session_id not in _envs:
        _envs[session_id] = BugTriageEnv()
    return _envs[session_id]


@app.post("/reset", response_model=ResetResult)
def reset(
    request: ResetRequest = None,
    x_session_id: Optional[str] = Header(default=DEFAULT_SESSION),
) -> ResetResult:
    """Reset the environment and return the initial observation."""
    if request is None:
        request = ResetRequest()
    env = _get_env(x_session_id)
    try:
        result = env.reset(
            task=request.task,
            scenario_id=request.scenario_id,
            seed=request.seed,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResult)
def step(
    action: Action,
    x_session_id: Optional[str] = Header(default=DEFAULT_SESSION),
) -> StepResult:
    """Take one action in the environment."""
    env = _get_env(x_session_id)
    try:
        result = env.step(action)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=StateResult)
def state(
    x_session_id: Optional[str] = Header(default=DEFAULT_SESSION),
) -> StateResult:
    """Return the current internal state of the environment."""
    return _get_env(x_session_id).state()


@app.get("/health")
def health():
    return {"status": "ok", "env": "bug-triage-openenv", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "Bug Triage OpenEnv",
        "tasks": ["bug_classify", "duplicate_detection", "full_triage"],
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
