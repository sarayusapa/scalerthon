# Bug Triage OpenEnv

An OpenEnv environment where AI agents triage real-world software bug reports — exactly the workflow engineering teams run daily on GitHub, Jira, and Linear.

## Why This Domain

Software teams collectively spend millions of engineering hours per year triaging issues: reading bug reports, classifying severity, spotting duplicates, drafting responses, and routing to the right team. Automating this with agents would have immediate industry impact. No existing OpenEnv environment targets this domain.

## Environment Description

The agent acts as a triage engineer for **Nexus Platform**, a fictional data analytics SaaS. It receives bug reports and must process them through a structured workflow:

| Action | Description |
|---|---|
| `classify` | Assign severity: critical / high / medium / low |
| `mark_duplicate` | Flag a backlog issue as a duplicate of the current one |
| `draft_response` | Write a professional reply to the reporter |
| `assign_labels` | Tag the issue with relevant labels |
| `submit` | Finalize and end the episode |

---

## Tasks

### Task 1 — `bug_classify` (Easy, max 5 steps)

**Objective:** Classify the severity of a single bug report.

**Scoring:**
- Exact match → `1.0`
- One severity level off → `0.5`
- Two levels off → `0.25`
- Three levels off → `0.0`

**Why it's easy:** Agent just needs to read one issue and output a severity. No multi-step planning required. A strong LLM should score ~0.8–1.0.

**Expected baseline score: ~0.85**

---

### Task 2 — `duplicate_detection` (Medium, max 10 steps)

**Objective:** Given a new issue and a backlog of 8 issues (2–3 are duplicates), identify all duplicates.

**Scoring:** F1 score over marked duplicates vs. ground-truth set.
- Correct duplicate found: `+0.20` per step
- False positive: `-0.10` per step
- Final score = F1(marked, actual)

**Why it's medium:** Duplicates are described with different terminology, different components mentioned, different symptoms — but share the same root cause. Requires reading comprehension and cross-issue reasoning.

**Expected baseline score: ~0.50**

---

### Task 3 — `full_triage` (Hard, max 15 steps)

**Objective:** Complete all triage steps before submitting.

**Scoring (weighted average):**
| Sub-task | Weight | Max |
|---|---|---|
| Severity classification | 30% | 1.0 |
| Duplicate detection (F1) | 30% | 1.0 |
| Response quality | 20% | 1.0 |
| Label assignment (F1) | 20% | 1.0 |

**Why it's hard:**
- Must complete all 4 sub-tasks within 15 steps
- Duplicates are non-obvious (same root cause, completely different description)
- Response must be professional, technically accurate, and contain relevant domain terms
- Labels must match expected domain vocabulary
- Step budget forces efficient ordering

**Expected baseline score: ~0.35**

---

## Action Space

```json
{
  "action_type": "classify | mark_duplicate | draft_response | assign_labels | submit",
  "severity": "critical | high | medium | low",      // for classify
  "duplicate_of": "NX-001",                          // for mark_duplicate
  "response_text": "Thank you for reporting...",      // for draft_response
  "labels": ["bug", "memory-leak", "integrations"]   // for assign_labels
}
```

## Observation Space

```json
{
  "task": "full_triage",
  "instructions": "You must complete...",
  "current_issue": {
    "id": "NX-043",
    "title": "Stream connector memory keeps growing...",
    "description": "...",
    "component": "integrations",
    "reporter": "senior_engineer",
    "reproduction_steps": "...",
    "environment_info": "..."
  },
  "backlog": [
    { "id": "NX-011", "title": "Memory leak in streaming...", "severity": "high", ... }
  ],
  "step": 2,
  "max_steps": 15,
  "triage_state": {
    "classified": true,
    "severity_assigned": "high",
    "duplicates_marked": [],
    "response_drafted": false,
    "labels_assigned": []
  },
  "available_actions": ["classify", "mark_duplicate", "draft_response", "assign_labels", "submit"],
  "available_labels": ["bug", "security", "memory-leak", ...],
  "last_action_feedback": "Classified as 'high'. Score: 1.00"
}
```

---

## Setup & Usage

### Local (Docker)

```bash
docker build -t bug-triage-openenv .
docker run -p 7860:7860 bug-triage-openenv
```

### Local (Python)

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860
```

### Test the API

```bash
# Reset to bug_classify task
curl -s -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "bug_classify", "scenario_id": 0, "seed": 42}' | python3 -m json.tool

# Take a classify action
curl -s -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "classify", "severity": "critical"}' | python3 -m json.tool

# Check state
curl -s http://localhost:7860/state | python3 -m json.tool
```

### Run Baseline Inference

```bash
export HF_TOKEN=<your_token>
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_URL=http://localhost:7860

python inference.py
```

---

## Baseline Scores

Run with `Qwen/Qwen2.5-72B-Instruct` via HF Router:

| Task | Score | Notes |
|---|---|---|
| `bug_classify` | ~0.85 | Occasionally confuses high↔critical |
| `duplicate_detection` | ~0.50 | Finds obvious dupes; misses non-obvious ones |
| `full_triage` | ~0.35 | Response quality and label precision drag score |
| **Mean** | **~0.57** | |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `HF_TOKEN` | Yes | Hugging Face API token |
| `API_BASE_URL` | No | LLM endpoint (default: HF router) |
| `MODEL_NAME` | No | Model ID (default: Qwen2.5-72B-Instruct) |
| `ENV_URL` | No | Environment URL (default: http://localhost:7860) |

---

## Reward Design Notes

**Partial progress signals throughout the episode:**
- `bug_classify`: single-shot partial credit via severity distance
- `duplicate_detection`: immediate `+0.20` per correct mark, `-0.10` per false positive, final F1
- `full_triage`: each sub-task yields reward independently — agent can see score improve step by step

**Penalties for undesirable behavior:**
- Repeated same action: `-0.05`
- Illegal action for task: `-0.05`
- False positive duplicates: `-0.10`

This design gives RL agents a dense signal while still rewarding correct final answers.
