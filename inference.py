"""
Bug Triage OpenEnv — Baseline Inference Script

Runs an LLM agent against all three tasks and emits structured logs.

Required env vars:
  HF_TOKEN or API_KEY   — API key for the LLM provider
  API_BASE_URL          — OpenAI-compatible endpoint (default: HF router)
  MODEL_NAME            — Model identifier

Optional:
  ENV_URL               — URL of the running Bug Triage env (default: http://localhost:7860)

Stdout format (mandatory):
  [START] task=<name> env=bug-triage-openenv model=<model>
  [STEP]  step=<n> action=<json> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""

import json
import os
import sys
import textwrap
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860").rstrip("/")
BENCHMARK = "bug-triage-openenv"

MAX_STEPS = {
    "bug_classify": 5,
    "duplicate_detection": 10,
    "full_triage": 15,
}
TEMPERATURE = 0.2
MAX_TOKENS = 512
SUCCESS_THRESHOLD = 0.5


# ── Logging helpers ────────────────────────────────────────────────────────────

def log_start(task: str, model: str) -> None:
    print(f"[START] task={task} env={BENCHMARK} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err = error if error else "null"
    done_s = str(done).lower()
    # Collapse action to single line, no internal newlines
    action_s = action.replace("\n", " ").replace("\r", "")
    print(f"[STEP] step={step} action={action_s} reward={reward:.2f} done={done_s} error={err}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_s = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_s}", flush=True)


# ── Environment HTTP client ────────────────────────────────────────────────────

def env_reset(task: str, scenario_id: int = 0, seed: int = 42) -> Dict[str, Any]:
    resp = requests.post(
        f"{ENV_URL}/reset",
        json={"task": task, "scenario_id": scenario_id, "seed": seed},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_step(action: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(f"{ENV_URL}/step", json=action, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _obs_to_text(obs: Dict[str, Any]) -> str:
    """Format observation as readable text for the LLM."""
    issue = obs.get("current_issue", {})
    state = obs.get("triage_state", {})
    backlog = obs.get("backlog", [])

    lines = [
        f"=== STEP {obs.get('step', '?')} / {obs.get('max_steps', '?')} ===",
        f"Task: {obs.get('task', '')}",
        "",
        "-- Current Issue --",
        f"ID:          {issue.get('id', '')}",
        f"Title:       {issue.get('title', '')}",
        f"Component:   {issue.get('component', '')}",
        f"Reporter:    {issue.get('reporter', '')}",
        f"Description: {issue.get('description', '')}",
    ]
    if issue.get("reproduction_steps"):
        lines.append(f"Repro Steps: {issue['reproduction_steps']}")
    if issue.get("environment_info"):
        lines.append(f"Environment: {issue['environment_info']}")

    if backlog:
        lines += ["", "-- Backlog Issues (potential duplicates) --"]
        for b in backlog:
            lines.append(
                f"  [{b['id']}] [{b['severity'].upper()}] {b['title']} "
                f"| component={b['component']}"
            )
            lines.append(f"           {b['description'][:120]}...")

    lines += [
        "",
        "-- Current Triage State --",
        f"  classified:       {state.get('classified', False)}",
        f"  severity_assigned:{state.get('severity_assigned', 'None')}",
        f"  duplicates_marked:{state.get('duplicates_marked', [])}",
        f"  response_drafted: {state.get('response_drafted', False)}",
        f"  labels_assigned:  {state.get('labels_assigned', [])}",
        "",
        "-- Available Actions --",
        f"  {obs.get('available_actions', [])}",
        "-- Available Labels --",
        f"  {obs.get('available_labels', [])}",
        "",
        f"-- Last Feedback -- {obs.get('last_action_feedback', '')}",
    ]
    return "\n".join(lines)


SYSTEM_PROMPTS = {
    "bug_classify": textwrap.dedent("""
        You are an expert software engineering triage agent.
        Your job: read the bug report and classify its severity.

        Severity definitions:
          critical — data loss, security vulnerability, authentication bypass, production down
          high     — major feature broken, significant user impact, no workaround
          medium   — non-critical feature degraded, workaround available
          low      — cosmetic issue, minor UX problem, typo, documentation

        Respond with ONLY a JSON object in this exact format:
        {"action_type": "classify", "severity": "<critical|high|medium|low>"}
    """).strip(),

    "duplicate_detection": textwrap.dedent("""
        You are an expert software triage agent specializing in duplicate detection.
        Your job: identify which backlog issues describe the SAME ROOT CAUSE as the new issue.

        Key insight: duplicates often use different words but describe the same underlying problem.
        Look for: same component, same failure mode, same symptoms (even if described differently).

        Available actions:
          mark_duplicate — call once per duplicate: {"action_type": "mark_duplicate", "duplicate_of": "<ISSUE-ID>"}
          submit         — when done: {"action_type": "submit"}

        Respond with ONLY a JSON object. One action per response.
        Be conservative: only mark something as duplicate if you are confident it is the SAME issue.
    """).strip(),

    "full_triage": textwrap.dedent("""
        You are an expert software engineering triage agent.
        You must complete a full triage of a bug report. Required steps (any order):
          1. classify       — {"action_type": "classify", "severity": "<critical|high|medium|low>"}
          2. mark_duplicate — {"action_type": "mark_duplicate", "duplicate_of": "<ISSUE-ID>"} (once per dupe)
          3. draft_response — {"action_type": "draft_response", "response_text": "<professional reply to reporter>"}
          4. assign_labels  — {"action_type": "assign_labels", "labels": ["label1", "label2", ...]}
          5. submit         — {"action_type": "submit"} (LAST step to finalize)

        Severity: critical=data loss/security, high=major feature broken, medium=degraded/workaround, low=cosmetic.
        Duplicates: same root cause, even if described differently. Be precise.
        Response: professional, acknowledge the issue, mention next steps, reference technical details.
        Labels: choose only from the provided available_labels list.

        Respond with ONLY a JSON object. One action per response.
    """).strip(),
}


def get_next_action(
    client: OpenAI,
    task: str,
    obs: Dict[str, Any],
    history: List[Dict],
) -> Dict[str, Any]:
    """Ask the LLM for the next action. Returns a parsed action dict."""
    obs_text = _obs_to_text(obs)

    messages = [{"role": "system", "content": SYSTEM_PROMPTS[task]}]
    # Include up to last 4 history turns for context
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": obs_text})

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}", flush=True)
        return {"action_type": "submit"}

    # Extract JSON from response
    try:
        # Handle markdown code blocks
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        action = json.loads(raw.strip())
        return action
    except json.JSONDecodeError:
        # Try to find JSON substring
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            action = json.loads(raw[start:end])
            return action
        except (ValueError, json.JSONDecodeError):
            print(f"[DEBUG] Could not parse JSON from: {raw!r}", flush=True)
            return {"action_type": "submit"}


# ── Episode runner ─────────────────────────────────────────────────────────────

def run_episode(client: OpenAI, task: str, scenario_id: int = 0) -> float:
    """Run one episode. Returns the final score [0, 1]."""
    log_start(task=task, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    history: List[Dict] = []
    error_msg: Optional[str] = None

    try:
        result = env_reset(task, scenario_id=scenario_id, seed=42)
        obs = result["observation"]

        for step_n in range(1, MAX_STEPS[task] + 1):
            # Check if already done from previous step
            ts = obs.get("triage_state", {})
            if ts.get("done", False):
                break

            action_dict = get_next_action(client, task, obs, history)
            action_str = json.dumps(action_dict)

            # Record assistant message in history for context
            history.append({"role": "assistant", "content": action_str})

            try:
                step_result = env_step(action_dict)
            except Exception as e:
                error_msg = str(e)
                log_step(step_n, action_str, 0.0, True, error_msg)
                rewards.append(0.0)
                steps_taken = step_n
                break

            reward = step_result.get("reward", 0.0)
            done = step_result.get("done", False)
            obs = step_result["observation"]
            info = step_result.get("info", {})
            error_msg = obs.get("last_action_feedback", None)

            rewards.append(reward)
            steps_taken = step_n
            log_step(step_n, action_str, reward, done, None)

            # Add feedback to history
            history.append({
                "role": "user",
                "content": f"[feedback] {obs.get('last_action_feedback', '')}"
            })

            if done:
                # Extract final score from info if available
                if "final_score" in info:
                    score = float(info["final_score"])
                else:
                    score = max(min(sum(rewards), 1.0), 0.0)
                break
        else:
            # Hit max steps without done
            score = max(min(sum(rewards), 1.0), 0.0)

        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)
        error_msg = str(e)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print("[ERROR] Set HF_TOKEN or API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    tasks = [
        ("bug_classify", 0),
        ("duplicate_detection", 0),
        ("full_triage", 0),
    ]

    all_scores = []
    for task, scenario_id in tasks:
        score = run_episode(client, task, scenario_id=scenario_id)
        all_scores.append(score)
        print(f"[INFO] {task} score: {score:.4f}", flush=True)

    mean_score = sum(all_scores) / len(all_scores)
    print(f"[INFO] Mean score across all tasks: {mean_score:.4f}", flush=True)


if __name__ == "__main__":
    main()
