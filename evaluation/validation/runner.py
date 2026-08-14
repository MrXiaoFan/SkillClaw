"""Compatibility wrapper for the renamed confirmation runner."""

from __future__ import annotations

from evaluation.confirmation.runner import run_case_confirmation, run_case_validators

__all__ = [
    "run_case_confirmation",
    "run_case_validators",
]
