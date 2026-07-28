"""Remote experiment environment helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .experiment_vm import RemoteExperimentVmClient, RemoteExperimentVmConfig

__all__ = ["RemoteExperimentVmClient", "RemoteExperimentVmConfig"]


def __getattr__(name: str) -> object:
    if name in __all__:
        from .experiment_vm import RemoteExperimentVmClient, RemoteExperimentVmConfig

        exports = {
            "RemoteExperimentVmClient": RemoteExperimentVmClient,
            "RemoteExperimentVmConfig": RemoteExperimentVmConfig,
        }
        return exports[name]
    raise AttributeError(name)
