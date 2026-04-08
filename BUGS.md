# Bugs & Loopholes

## Critical Bugs

**1. Whitespace response locks draft slot permanently**
`draft_response` with `"   "` sets `response_drafted = True` despite no real content.
Agent can never draft again that episode. Label sub-task score = 0.0 permanently.
- `environment.py:283` — only checks `not action.response_text`, misses whitespace-only strings

**2. Invalid labels silently accepted**
`assign_labels(["fake-label", "invented", "bug"])` is stored and graded with partial credit.
Zero validation against `AVAILABLE_LABELS`.
- `environment.py:295-311`

**3. full_triage cumulative reward disconnected from final score**
Sub-task rewards issued during episode (classify=0.30, response=0.20, labels=0.20).
But `_compute_full_triage_final()` at submit recalculates from scratch independently.
`cumulative_reward` in state and `final_score` in info can diverge — agent has no honest running total.
- `environment.py:350-365`

---

## Grader Loopholes

**4. Response quality grader is keyword-stuffable**
`"thank fix resolv investigat memory cache"` — nonsense — scores 1.0.
A well-written professional response without those exact substrings scores 0.5.
Rewards keyword presence, not coherence.
- `graders.py:86-121`

**5. Labels not validated against AVAILABLE_LABELS in grader**
`grade_labels` accepts any strings. Misspelled or invented labels get partial F1 credit with no penalty.
- `graders.py:124-138`

---

## Logic Issues

**6. mark_duplicate check order is fragile**
`step_reward_duplicate()` runs before the backlog membership check.
If ID is not in backlog, reward is computed as -0.1 (false positive) then overridden to -0.05.
Correct by accident, fragile by design.
- `environment.py:261-278`

**7. bug_classify has no exit if agent refuses to classify**
`submit` not in `AVAILABLE_ACTIONS["bug_classify"]`. Agent burning all 5 steps with illegal
actions costs the same (-0.05/step) as doing nothing useful. No additional penalty for full non-compliance.

**8. scenario_id wraps silently via modulo**
`env.reset(task='bug_classify', scenario_id=999)` silently loads scenario 3.
No warning or error. Eval scripts passing wrong IDs get a different scenario with no indication.
- `environment.py:140`

---

## Minor Issues

**9. inference.py [END] line doesn't match spec**
Spec:   `[END] success=... steps=... rewards=...`
Actual: `[END] success=... steps=... score=... rewards=...`
Extra `score=` field not in spec.
- `inference.py:62`

**10. Single global env instance — no session isolation**
`_env = BugTriageEnv()` shared by all HTTP clients.
Two concurrent callers reset each other's episodes.
- `main.py:35`

**11. Thin scenario coverage**
- `full_triage`: only 2 scenarios
- `duplicate_detection`: only 3 scenarios
Wraps silently (bug #8) so evaluator can see same scenario twice without knowing it.
