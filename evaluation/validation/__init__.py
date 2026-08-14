"""Compatibility wrapper for the renamed confirmation package."""

from .core import *  # noqa: F401,F403
from .runner import run_case_confirmation, run_case_validators

__all__ = [
    "run_case_confirmation",
    "run_case_validators",
]
