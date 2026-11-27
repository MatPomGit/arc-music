"""Pure offline P09 task state; no personal text, prompts, storage or network."""
from dataclasses import dataclass, replace
import math

WINDOW_SECONDS = 480.


@dataclass(frozen=True)
class Task:
    music: int
    elapsed: float = 0.
    selection: int | None = None
    previews: tuple = ()
    stopped: bool = False


def start(music):
    if type(music) is not int or music not in (0,1):
        raise ValueError("Invalid assignment")
    return Task(music)


def transition(state, action, elapsed, candidate=None):
    """Use server monotonic elapsed time in an eventual authenticated service."""
    if state.stopped or state.elapsed >= WINDOW_SECONDS:
        raise ValueError("Task already ended")
    if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not state.elapsed <= elapsed <= WINDOW_SECONDS:
        raise ValueError("Invalid elapsed time")
    if action in ("preview","select"):
        if elapsed == WINDOW_SECONDS or type(candidate) is not int or candidate not in range(1,7):
            raise ValueError("Invalid candidate or expired task")
        if action == "preview":
            return replace(state, elapsed=elapsed,
                           previews=tuple(sorted(set(state.previews)|{candidate})))
        if candidate not in state.previews:
            raise ValueError("Preview required before selection")
        return replace(state, elapsed=elapsed, selection=candidate)
    if candidate is not None:
        raise ValueError("Unexpected candidate")
    if action == "stop":
        return replace(state, elapsed=elapsed, stopped=True)
    if action == "finish" and elapsed == WINDOW_SECONDS:
        return replace(state, elapsed=elapsed)
    raise ValueError("Invalid action")


def summary(state):
    return dict(music=state.music, selected=state.selection, preview_count=len(state.previews),
                elapsed=state.elapsed, completed=state.elapsed==WINDOW_SECONDS and not state.stopped
                and state.selection is not None, stopped=state.stopped)
