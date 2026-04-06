"""
Bug Triage Environment — core state machine.

Three tasks of increasing difficulty:
  1. bug_classify      (easy)   — classify severity of a single issue
  2. duplicate_detection (medium) — find duplicate issues in a backlog
  3. full_triage       (hard)  — classify + dedupe + draft response + label
"""

import random
from typing import Any, Dict, List, Optional

from data import (
    AVAILABLE_LABELS,
    BUG_CLASSIFY_SCENARIOS,
    DUPLICATE_DETECTION_SCENARIOS,
    FULL_TRIAGE_SCENARIOS,
    ISSUE_BANK,
)
from graders import (
    compute_full_triage_score,
    grade_duplicates,
    grade_labels,
    grade_response_quality,
    grade_severity,
    step_reward_duplicate,
)
from models import (
    Action,
    BacklogIssue,
    IssueReport,
    Observation,
    ResetResult,
    StateResult,
    StepResult,
    TriageState,
)

TASK_MAX_STEPS = {
    "bug_classify": 5,
    "duplicate_detection": 10,
    "full_triage": 15,
}

TASK_INSTRUCTIONS = {
    "bug_classify": (
        "You are triaging a software bug report. "
        "Read the issue carefully and call the 'classify' action with the correct severity. "
        "Severity levels: critical (data loss / security / service down), "
        "high (major feature broken, significant user impact), "
        "medium (feature degraded, workaround available), "
        "low (cosmetic, documentation, minor UX). "
        "You have at most {max_steps} steps. Call 'classify' to finish."
    ),
    "duplicate_detection": (
        "You are reviewing a new issue against an existing backlog. "
        "Call 'mark_duplicate' for each backlog issue that is a duplicate of the new issue. "
        "Two issues are duplicates if they describe the same root cause (even if symptoms differ). "
        "Call 'submit' when you are done marking duplicates. "
        "Correct marks earn +0.20 reward; false positives cost -0.10. "
        "You have at most {max_steps} steps."
    ),
    "full_triage": (
        "You are performing a complete triage of a new bug report. "
        "You must complete ALL of the following steps (in any order) before calling 'submit':\n"
        "  1. classify  — assign the correct severity\n"
        "  2. mark_duplicate — mark each backlog issue that is a duplicate (call once per duplicate)\n"
        "  3. draft_response — write a professional response to the reporter\n"
        "  4. assign_labels — assign relevant labels from the available list\n"
        "  5. submit — finalize the triage\n"
        "Scoring: severity 30%, duplicate F1 30%, response quality 20%, label F1 20%. "
        "You have at most {max_steps} steps."
    ),
}

AVAILABLE_ACTIONS = {
    "bug_classify": ["classify"],
    "duplicate_detection": ["mark_duplicate", "submit"],
    "full_triage": ["classify", "mark_duplicate", "draft_response", "assign_labels", "submit"],
}


def _make_issue(issue_id: str) -> IssueReport:
    raw = ISSUE_BANK[issue_id]
    return IssueReport(
        id=raw["id"],
        title=raw["title"],
        description=raw["description"],
        reporter=raw["reporter"],
        created_at=raw["created_at"],
        component=raw["component"],
        reproduction_steps=raw.get("reproduction_steps"),
        environment_info=raw.get("environment_info"),
    )


def _make_backlog_issue(issue_id: str) -> BacklogIssue:
    raw = ISSUE_BANK[issue_id]
    return BacklogIssue(
        id=raw["id"],
        title=raw["title"],
        description=raw["description"],
        severity=raw["severity"],
        labels=raw["labels"],
        status="open",
        component=raw["component"],
    )


class BugTriageEnv:
    """Stateful bug triage environment."""

    def __init__(self) -> None:
        self._state: Optional[TriageState] = None
        self._scenario: Optional[Dict[str, Any]] = None
        self._current_issue: Optional[IssueReport] = None
        self._backlog: List[BacklogIssue] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def reset(
        self,
        task: str = "bug_classify",
        scenario_id: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> ResetResult:
        rng = random.Random(seed)

        if task == "bug_classify":
            scenarios = BUG_CLASSIFY_SCENARIOS
        elif task == "duplicate_detection":
            scenarios = DUPLICATE_DETECTION_SCENARIOS
        elif task == "full_triage":
            scenarios = FULL_TRIAGE_SCENARIOS
        else:
            raise ValueError(f"Unknown task: {task}")

        if scenario_id is None:
            scenario_id = rng.randint(0, len(scenarios) - 1)
        scenario_id = scenario_id % len(scenarios)
        self._scenario = scenarios[scenario_id]

        max_steps = TASK_MAX_STEPS[task]
        self._state = TriageState(
            task=task,
            scenario_id=scenario_id,
            max_steps=max_steps,
        )

        # Build issue and backlog
        if task == "bug_classify":
            self._current_issue = _make_issue(self._scenario["issue_id"])
            self._backlog = []
        elif task == "duplicate_detection":
            self._current_issue = _make_issue(self._scenario["new_issue_id"])
            self._backlog = [_make_backlog_issue(bid) for bid in self._scenario["backlog_ids"]]
        else:  # full_triage
            self._current_issue = _make_issue(self._scenario["issue_id"])
            self._backlog = [_make_backlog_issue(bid) for bid in self._scenario["backlog_ids"]]

        obs = self._make_observation(feedback="Episode started. Read the issue and begin triage.")
        return ResetResult(observation=obs, info={"task": task, "scenario_id": scenario_id})

    def step(self, action: Action) -> StepResult:
        if self._state is None:
            raise RuntimeError("Call reset() before step()")
        if self._state.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._state.step += 1
        reward = 0.0
        done = False
        feedback = ""
        info: Dict[str, Any] = {}

        task = self._state.task

        # ── Validate action is legal for this task ──────────────────────────
        allowed = AVAILABLE_ACTIONS[task]
        if action.action_type not in allowed:
            feedback = f"Action '{action.action_type}' is not allowed in task '{task}'. Allowed: {allowed}."
            reward = -0.05
        else:
            reward, done, feedback, info = self._dispatch(action)

        # ── Step limit ─────────────────────────────────────────────────────
        if self._state.step >= self._state.max_steps and not done:
            done = True
            feedback += " [Max steps reached — episode ending.]"
            # Compute final score for partial work
            if task == "full_triage":
                final = self._compute_full_triage_final()
                info["final_score"] = final
            elif task == "duplicate_detection":
                dg = grade_duplicates(
                    self._state.duplicates_marked,
                    self._scenario["actual_duplicates"],
                    self._scenario["backlog_ids"],
                )
                info["duplicate_grades"] = dg

        self._state.cumulative_reward = round(self._state.cumulative_reward + reward, 4)
        if done:
            self._state.done = True

        obs = self._make_observation(feedback=feedback)
        return StepResult(observation=obs, reward=round(reward, 4), done=done, info=info)

    def state(self) -> StateResult:
        if self._state is None:
            return StateResult(state=TriageState(), info={"ready": False})
        return StateResult(state=self._state, info={"ready": True})

    # ── Internal dispatch ──────────────────────────────────────────────────────

    def _dispatch(self, action: Action):
        task = self._state.task
        at = action.action_type

        if at == "classify":
            return self._handle_classify(action)
        elif at == "mark_duplicate":
            return self._handle_mark_duplicate(action)
        elif at == "draft_response":
            return self._handle_draft_response(action)
        elif at == "assign_labels":
            return self._handle_assign_labels(action)
        elif at == "submit":
            return self._handle_submit()
        else:
            return -0.05, False, f"Unknown action: {at}", {}

    def _handle_classify(self, action: Action):
        task = self._state.task
        if self._state.classified:
            return -0.05, False, "Already classified. You cannot classify again.", {}

        score = grade_severity(action.severity, self._scenario["correct_severity"])
        self._state.classified = True
        self._state.severity_assigned = action.severity

        feedback = (
            f"Classified as '{action.severity}'. "
            f"Score: {score:.2f} (correct: {self._scenario['correct_severity']})."
        )

        if task == "bug_classify":
            # Task ends immediately after classification
            reward = score
            return reward, True, feedback, {"final_score": score, "correct_severity": self._scenario["correct_severity"]}
        else:
            # Partial reward in full_triage
            reward = score * 0.30
            return round(reward, 4), False, feedback, {}

    def _handle_mark_duplicate(self, action: Action):
        issue_id = action.duplicate_of
        if not issue_id:
            return -0.05, False, "mark_duplicate requires 'duplicate_of' (issue ID).", {}

        backlog_ids = [b.id for b in self._backlog]
        actual_dupes = self._scenario.get("actual_duplicates", [])

        r = step_reward_duplicate(issue_id, actual_dupes, self._state.duplicates_marked)

        if issue_id in self._state.duplicates_marked:
            feedback = f"Issue {issue_id} was already marked as duplicate."
        elif issue_id not in backlog_ids:
            feedback = f"Issue {issue_id} is not in the backlog."
            r = -0.05
        elif issue_id in actual_dupes:
            self._state.duplicates_marked.append(issue_id)
            feedback = f"Marked {issue_id} as duplicate. This is correct! (+{r:.2f})"
        else:
            self._state.duplicates_marked.append(issue_id)
            feedback = f"Marked {issue_id} as duplicate. This is a false positive. ({r:.2f})"

        return round(r, 4), False, feedback, {}

    def _handle_draft_response(self, action: Action):
        if self._state.response_drafted:
            return -0.05, False, "Response already drafted. You cannot draft again.", {}
        if not action.response_text:
            return -0.05, False, "draft_response requires 'response_text'.", {}

        keywords = self._scenario.get("response_quality_keywords", [])
        score = grade_response_quality(action.response_text, keywords)
        self._state.response_drafted = True
        self._state.response_text = action.response_text

        reward = score * 0.20  # score in [0, 1], weight 20%
        feedback = f"Response drafted. Quality score: {score:.2f}/1.00 (weighted reward: {reward:.2f})."
        return round(reward, 4), False, feedback, {}

    def _handle_assign_labels(self, action: Action):
        if self._state.labels_assigned:
            return -0.05, False, "Labels already assigned. You cannot assign again.", {}
        if not action.labels:
            return -0.05, False, "assign_labels requires 'labels' (list of strings).", {}

        expected = self._scenario.get("expected_labels", [])
        score = grade_labels(action.labels, expected)
        self._state.labels_assigned = action.labels

        reward = score * 0.20  # weight 20%
        feedback = (
            f"Assigned labels: {action.labels}. "
            f"Label F1: {score:.2f} vs expected {expected}. "
            f"Reward: {reward:.2f}."
        )
        return round(reward, 4), False, feedback, {}

    def _handle_submit(self):
        task = self._state.task

        if task == "duplicate_detection":
            dg = grade_duplicates(
                self._state.duplicates_marked,
                self._scenario["actual_duplicates"],
                [b.id for b in self._backlog],
            )
            final = dg["f1"]
            feedback = (
                f"Submitted. Duplicate detection F1: {final:.2f} "
                f"(TP={dg['true_positives']}, FP={dg['false_positives']}, FN={dg['false_negatives']})."
            )
            return round(final - self._state.cumulative_reward, 4), True, feedback, {
                "final_score": final,
                "duplicate_grades": dg,
            }

        elif task == "full_triage":
            final = self._compute_full_triage_final()
            missing = []
            if not self._state.classified:
                missing.append("classify")
            if not self._state.response_drafted:
                missing.append("draft_response")
            if not self._state.labels_assigned:
                missing.append("assign_labels")
            feedback = (
                f"Submitted. Final triage score: {final:.2f}. "
                + (f"Missing steps: {missing}. " if missing else "All steps completed. ")
            )
            return 0.0, True, feedback, {"final_score": final}

        else:
            return 0.0, True, "Submitted.", {"final_score": self._state.cumulative_reward}

    def _compute_full_triage_final(self) -> float:
        sev_score = grade_severity(self._state.severity_assigned, self._scenario["correct_severity"])
        dg = grade_duplicates(
            self._state.duplicates_marked,
            self._scenario["actual_duplicates"],
            [b.id for b in self._backlog],
        )
        resp_score = grade_response_quality(
            self._state.response_text,
            self._scenario.get("response_quality_keywords", []),
        )
        label_score = grade_labels(
            self._state.labels_assigned,
            self._scenario.get("expected_labels", []),
        )
        return compute_full_triage_score(sev_score, dg, resp_score, label_score)

    # ── Observation builder ────────────────────────────────────────────────────

    def _make_observation(self, feedback: str = "") -> Observation:
        task = self._state.task
        instr = TASK_INSTRUCTIONS[task].format(max_steps=self._state.max_steps)
        return Observation(
            task=task,
            instructions=instr,
            current_issue=self._current_issue,
            backlog=self._backlog,
            step=self._state.step,
            max_steps=self._state.max_steps,
            triage_state=self._state,
            available_actions=AVAILABLE_ACTIONS[task],
            available_labels=AVAILABLE_LABELS,
            last_action_feedback=feedback,
        )
