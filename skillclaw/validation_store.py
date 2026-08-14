"""Compatibility wrapper for the renamed replay gate store."""

from __future__ import annotations

from .replay_gate_store import ReplayGateStore, ValidationStore

__all__ = [
    "ReplayGateStore",
    "ValidationStore",
]
