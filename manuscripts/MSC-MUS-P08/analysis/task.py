"""Offline P08 manipulation contract; no network or participant storage."""
from dataclasses import dataclass

STAGES = ("rhythm", "harmony", "instrument", "ending")
DECISION_WINDOW = 10.0


@dataclass(frozen=True)
class StageResult:
    selected: int
    applied: int | None


def evaluate_stage(authority, manual, rule_choice, preference, action_seconds):
    """A manual confirmation queues application at the shared deadline.

    A missed confirmation leaves the current arrangement in place.
    """
    if any(type(value) is not int or value not in (0, 1)
           for value in (authority, manual, rule_choice, preference)):
        raise ValueError("Expected binary assignment and candidate indices")
    selected = preference if authority else rule_choice
    if action_seconds is not None and (
        not manual or not 0 <= action_seconds <= DECISION_WINDOW
    ):
        raise ValueError("Invalid manual confirmation")
    applied = selected if not manual or action_seconds is not None else None
    return StageResult(selected, applied)


def system_choices(sequence):
    """Freeze one balanced two-option sequence for each assigned participant."""
    if type(sequence) is not int or sequence < 0:
        raise ValueError("Invalid sequence index")
    return tuple((sequence % 16 >> stage) & 1 for stage in range(len(STAGES)))
