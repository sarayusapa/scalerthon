"""
Deterministic graders for the three Bug Triage tasks.

All graders return a float in [0.0, 1.0].
"""

from typing import List, Optional, Set
from data import SEVERITY_ORDER


# ── Task 1: Bug Severity Classification ───────────────────────────────────────

def grade_severity(predicted: Optional[str], correct: str) -> float:
    """
    Partial-credit severity grading.
    Distance 0 → 1.0, distance 1 → 0.5, distance 2 → 0.25, distance 3 → 0.0.
    """
    if predicted is None:
        return 0.0
    predicted = predicted.lower().strip()
    correct = correct.lower().strip()
    if predicted == correct:
        return 1.0
    if predicted not in SEVERITY_ORDER or correct not in SEVERITY_ORDER:
        return 0.0
    dist = abs(SEVERITY_ORDER.index(predicted) - SEVERITY_ORDER.index(correct))
    return max(0.0, {0: 1.0, 1: 0.5, 2: 0.25, 3: 0.0}.get(dist, 0.0))


# ── Task 2: Duplicate Detection ────────────────────────────────────────────────

def grade_duplicates(
    marked: List[str],
    actual: List[str],
    backlog_ids: List[str],
) -> dict:
    """
    F1-based grading with partial per-step signals.

    Returns:
        {
          "f1": float,
          "precision": float,
          "recall": float,
          "true_positives": int,
          "false_positives": int,
          "false_negatives": int,
        }
    """
    marked_set: Set[str] = set(marked)
    actual_set: Set[str] = set(actual)
    backlog_set: Set[str] = set(backlog_ids)

    # Only count marks that are actually in the backlog
    valid_marks = marked_set & backlog_set

    tp = len(valid_marks & actual_set)
    fp = len(valid_marks - actual_set)
    fn = len(actual_set - valid_marks)

    # Both sets empty → agent correctly identified no duplicates → perfect score
    if len(actual_set) == 0 and len(valid_marks) == 0:
        return {
            "f1": 1.0, "precision": 1.0, "recall": 1.0,
            "true_positives": 0, "false_positives": 0, "false_negatives": 0,
        }

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def step_reward_duplicate(issue_id: str, actual_duplicates: List[str], already_marked: List[str]) -> float:
    """Immediate per-step reward when agent calls mark_duplicate."""
    if issue_id in already_marked:
        return -0.05  # Already marked — penalise redundancy
    if issue_id in actual_duplicates:
        return 0.2    # Correct duplicate found
    return -0.1       # False positive


# ── Task 3: Full Triage ────────────────────────────────────────────────────────

def grade_response_quality(text: Optional[str], keywords: List[str]) -> float:
    """
    Score a drafted response on 4 dimensions (each worth 0.25):
      1. Minimum substance (>= 40 chars AND >= 8 unique words — blocks keyword stuffing)
      2. Polite acknowledgement
      3. Mentions relevant technical terms from the issue
      4. Describes next steps / resolution intent

    Returns a value in [0.0, 1.0].
    """
    if not text or len(text.strip()) < 20:
        return 0.0

    text_lower = text.lower()
    words = text_lower.split()
    unique_words = set(words)
    score = 0.0

    # Substance check — length, prose structure (punctuation), AND connector words.
    # Real sentences contain articles/pronouns/prepositions; keyword dumps do not.
    _connectors = {"the", "a", "an", "we", "our", "you", "your", "is", "are",
                   "will", "have", "has", "this", "that", "for", "with", "and",
                   "not", "it", "to", "in", "of", "on", "at", "been"}
    connector_count = sum(1 for w in words if w in _connectors)
    has_prose_structure = any(c in text for c in ".!?")
    if len(text.strip()) >= 40 and has_prose_structure and connector_count >= 3:
        score += 0.25

    # Acknowledgement / politeness
    ack_words = {"thank", "appreciate", "understand", "acknowledge", "sorry", "apolog"}
    if any(w in text_lower for w in ack_words):
        score += 0.25

    # Technical relevance — matches any expected keyword
    if any(kw.lower() in text_lower for kw in keywords):
        score += 0.25

    # Next-steps intent
    next_step_words = {"investigat", "fix", "resolv", "priorit", "schedul", "look into",
                       "reproduc", "patch", "deploy", "release", "workaround", "escalat"}
    if any(w in text_lower for w in next_step_words):
        score += 0.25

    return round(score, 4)


def grade_labels(assigned: List[str], expected: List[str]) -> float:
    """
    F1 score over label sets.
    Caller is responsible for pre-filtering assigned to valid labels only.
    """
    assigned_set = set(assigned)
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    tp = len(assigned_set & expected_set)
    fp = len(assigned_set - expected_set)
    fn = len(expected_set - assigned_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return round(f1, 4)


def compute_full_triage_score(
    severity_score: float,
    duplicate_grades: dict,
    response_score: float,
    label_score: float,
) -> float:
    """
    Weighted combination:
      - Severity classification : 30%
      - Duplicate detection (F1): 30%
      - Response quality        : 20%
      - Label assignment (F1)   : 20%
    """
    weighted = (
        severity_score * 0.30
        + duplicate_grades["f1"] * 0.30
        + response_score * 0.20   # response_score in [0, 1]
        + label_score * 0.20
    )
    return round(min(max(weighted, 0.0), 1.0), 4)
