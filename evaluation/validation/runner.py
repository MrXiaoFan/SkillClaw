from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .checks import default_registry
from .core import ValidationContext, summarize_checks


def run_case_validators(
    case: dict[str, Any],
    root: Path,
    *,
    case_path: Path | None = None,
    agent_output_path: Path | None = None,
    skip_commands: bool = False,
) -> dict[str, Any]:
    ctx = ValidationContext(
        case=case,
        root=root,
        case_path=case_path,
        agent_output_path=agent_output_path,
        skip_commands=skip_commands,
    )
    registry = default_registry()
    checks: list[dict[str, Any]] = []
    for spec in case.get("validators", []) or []:
        if not isinstance(spec, dict):
            continue
        if spec.get("enabled", True) is False:
            checks.append(
                {
                    "name": spec.get("name"),
                    "type": spec.get("type"),
                    "allow_failure": bool(spec.get("allow_failure")),
                    "status": "skipped",
                    "reason": "disabled",
                }
            )
            continue
        checks.append(registry.run(ctx, spec))

    return {
        "case_id": case.get("case_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validator_mode": "case-level",
        "target_root": str(root),
        "agent_output_path": str(agent_output_path) if agent_output_path else "",
        "status": summarize_checks(checks),
        "checks": checks,
    }
