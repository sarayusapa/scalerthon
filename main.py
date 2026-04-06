"""
FastAPI server for the Bug Triage OpenEnv environment.
Exposes: POST /reset, POST /step, GET /state
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

# Single-session global environment instance
_env = BugTriageEnv()


@app.post("/reset", response_model=ResetResult)
def reset(request: ResetRequest = None) -> ResetResult:
    """Reset the environment and return the initial observation."""
    if request is None:
        request = ResetRequest()
    try:
        result = _env.reset(
            task=request.task,
            scenario_id=request.scenario_id,
            seed=request.seed,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResult)
def step(action: Action) -> StepResult:
    """Take one action in the environment."""
    try:
        result = _env.step(action)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=StateResult)
def state() -> StateResult:
    """Return the current internal state of the environment."""
    return _env.state()


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
