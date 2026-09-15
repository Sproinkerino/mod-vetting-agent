from __future__ import annotations

from collections.abc import Callable


class JobCancelled(Exception):
    """Raised at a safe stage boundary after a user cancels a job."""


def ensure_not_cancelled(should_cancel: Callable[[], bool] | None) -> None:
    if should_cancel and should_cancel():
        raise JobCancelled("Investigation cancelled")