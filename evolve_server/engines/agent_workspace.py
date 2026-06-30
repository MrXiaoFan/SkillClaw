"""
Workspace management for the agent engine under ``evolve_server``.

Handles preparing the local workspace directory that OpenClaw operates on,
snapshotting skill state before agent execution, and collecting changes
(new / modified skill bundles) after the agent finishes.

Key design note on OpenClaw bootstrap integration:
  OpenClaw's ``ensureAgentWorkspace()`` creates template bootstrap files
  (AGENTS.md, SOUL.md, USER.md, IDENTITY.md, …) using ``writeFileIfMissing``
  with ``flag: 'wx'`` — it will NOT overwrite files that already exist.
  We exploit this by pre-writing our own versions of these files during
  ``prepare()`` so OpenClaw picks them up as-is.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from skillclaw.skill_bundle import (
    bundle_entrypoint_text,
    bundle_tree_sha256,
    read_skill_bundle,
    write_skill_bundle,
)

from ..core.utils import parse_skill_content

logger = logging.getLogger(__name__)

_TEXT_BUNDLE_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def _format_feedback_bundle_summary(records: list[dict[str, Any]]) -> str:
    """Render a compact Markdown summary for validator-backed skill feedback."""
    lines = [
        "# Validator-Backed Skill Feedback Summary",
        "",
        "Use this file as a high-signal index before reading the full JSON bundle.",
        "Prefer these validator-backed signals over speculative interpretations of session text alone.",
        "",
        "| Skill | Gate | Runs | Mean | Loc | CVE | CVE Miss | Validator |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        summary = record.get("summary") or {}
        dims = record.get("dimensions") or {}
        lines.append(
            "| {skill} | {gate} | {runs} | {mean:.2f} | {loc} | {cve} | {cve_miss} | {validator} |".format(
                skill=record.get("skill", ""),
                gate=record.get("gate_decision", ""),
                runs=int(summary.get("selected_runs", 0) or 0),
                mean=float(summary.get("mean_score", 0.0) or 0.0),
                loc=int(dims.get("localization_success", 0) or 0),
                cve=int(dims.get("cve_success", 0) or 0),
                cve_miss=int(dims.get("cve_calibration_miss", 0) or 0),
                validator=int(dims.get("validator_passed", 0) or 0),
            )
        )
    lines.extend(
        [
            "",
            "## How To Use",
            "",
            "- Treat `gate_decision=revise` as evidence that the skill is useful but incomplete.",
            "- Treat `cve_calibration_miss>0` as a sign that localization and exact CVE identity must be separated.",
            "- Read `revision_directives` in the JSON before editing any selected skill.",
        ]
    )
    return "\n".join(lines) + "\n"


def _format_feedback_gate_playbook(records: list[dict[str, Any]]) -> str:
    """Render an action-oriented playbook from gate decisions."""
    grouped: dict[str, list[dict[str, Any]]] = {
        "revise": [],
        "demote": [],
        "keep": [],
        "promote": [],
        "insufficient_evidence": [],
    }
    for record in records:
        decision = str(record.get("gate_decision") or "").strip().lower()
        grouped.setdefault(decision, []).append(record)

    lines = [
        "# Gate Decision Playbook",
        "",
        "Use this file to translate validator-backed gate decisions into editing behavior.",
        "",
        "## Required Behavior By Gate",
        "",
        "- `revise`: edit the skill conservatively. Preserve sections that already support localization or evidence, and focus only on the failing dimension named in `revision_directives`.",
        "- `demote`: do not improve this skill for the current task family unless the evidence clearly shows it is still relevant. Prefer narrowing retrieval boundaries and adding stronger `NOT for:` exclusions.",
        "- `keep`: avoid speculative edits. Keep the skill unchanged unless a small clarification is directly supported by the evidence.",
        "- `promote`: avoid rewriting. At most, preserve current structure and record why the skill is stable.",
        "- `insufficient_evidence`: do not change the skill unless there is an obvious correctness bug independent of the current evidence volume.",
        "",
    ]
    for decision in ("revise", "demote", "keep", "promote", "insufficient_evidence"):
        items = grouped.get(decision) or []
        if not items:
            continue
        lines.append(f"## {decision}")
        lines.append("")
        for record in items:
            skill = str(record.get("skill") or "")
            directives = record.get("revision_directives") or []
            dims = record.get("dimensions") or {}
            summary = record.get("summary") or {}
            lines.append(f"### {skill}")
            lines.append("")
            lines.append(
                "- Evidence snapshot: runs={runs}, mean_score={mean:.2f}, "
                "localization={loc}, cve={cve}, cve_miss={cve_miss}, validator_passed={validator}".format(
                    runs=int(summary.get("selected_runs", 0) or 0),
                    mean=float(summary.get("mean_score", 0.0) or 0.0),
                    loc=int(dims.get("localization_success", 0) or 0),
                    cve=int(dims.get("cve_success", 0) or 0),
                    cve_miss=int(dims.get("cve_calibration_miss", 0) or 0),
                    validator=int(dims.get("validator_passed", 0) or 0),
                )
            )
            if directives:
                lines.append("- Revision directives:")
                for directive in directives:
                    lines.append(f"  - {directive}")
            else:
                lines.append("- Revision directives: none")
            lines.append("")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _augment_agents_md_with_feedback(agents_md: str, feedback_rel_path: str) -> str:
    return (
        agents_md.rstrip()
        + "\n\n---\n\n"
        + "## Validator-backed feedback available in this workspace\n\n"
        + f"A structured validator-backed feedback bundle is available at `{feedback_rel_path}`.\n"
        + "Before changing a skill, read this bundle and prefer its evidence over session-text impressions alone.\n"
        + "Also read `feedback/PLAYBOOK.md` and follow its gate-specific editing behavior.\n"
        + "Pay special attention to:\n"
        + "- `gate_decision`\n"
        + "- `revision_directives`\n"
        + "- `dimensions.localization_success`\n"
        + "- `dimensions.cve_success`\n"
        + "- `dimensions.cve_calibration_miss`\n"
        + "- per-case `validator_checks`\n"
    )


def _normalize_text_bundle_newlines(bundle_files: dict[str, bytes]) -> dict[str, bytes]:
    """Normalize text bundle newlines for stable cross-platform evolution diffs.

    Windows ``Path.write_text()`` can materialize ``\r\n`` in agent workspaces.
    Skill bundles may also contain binary payloads, so only normalize common
    text-like files and skip data containing NUL bytes.
    """
    normalized: dict[str, bytes] = {}
    for rel_path, data in bundle_files.items():
        suffix = Path(rel_path).suffix.lower()
        if suffix in _TEXT_BUNDLE_SUFFIXES and b"\0" not in data:
            normalized[rel_path] = data.replace(b"\r\n", b"\n")
        else:
            normalized[rel_path] = data
    return normalized


# ---------------------------------------------------------------------------
# Custom bootstrap templates for the evolve-only workspace
# ---------------------------------------------------------------------------

_EVOLVE_AGENTS_MD = """\
# Skill Evolution Agent

You are a **skill evolution engineer**. Your sole task is to analyze agent
session data in this workspace and evolve the skill library.

## First Step — ALWAYS

Read `EVOLVE_AGENTS.md` in this workspace **before doing anything else**.
It contains the full methodology, workspace layout, editing principles,
and all instructions you need.

```
cat EVOLVE_AGENTS.md
```

## Workspace Quick Reference

```
workspace/
├── EVOLVE_AGENTS.md   ← full evolution methodology (READ THIS FIRST)
├── feedback/          ← validator-backed skill feedback bundle (if present)
│   ├── skill_feedback_bundle_latest.json
│   └── SUMMARY.md
├── sessions/          ← agent session JSON files to analyze
├── skills/            ← current skill library (read + write)
│   └── <name>/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── assets/
│       └── history/
├── manifest.json      ← skill manifest (read-only)
└── skill_registry.json
```

## Constraints

- **All file operations** stay within this workspace directory.
- Do NOT modify `sessions/`, `manifest.json`, or `skill_registry.json`.
- Do NOT modify `feedback/` artifacts; they are read-only evidence for this round.
- Write changes only inside `skills/<name>/` bundles.
- You may inspect and edit `SKILL.md`, `references/`, `scripts/`, `assets/`,
  `history/`, and other supporting files that belong to a skill.
- If there are no actionable patterns, make no changes — that is fine.
- Before finalizing any changed skill, complete the self-validation required
  by `EVOLVE_AGENTS.md`; if validation fails, keep editing or revert the
  change rather than leaving a known-failing skill in `skills/`.
- Record self-validation results in the paired `history/v<N>_evidence.md` file.
- When `feedback/` exists, every changed skill's `history/v<N>_evidence.md`
  must cite the applicable `gate_decision` and the `revision_directives` it followed.

## Memory

You may use `memory/` and `MEMORY.md` for long-term notes across rounds.
Append daily observations to `memory/YYYY-MM-DD.md`. Keep `MEMORY.md` for
curated, high-level summaries of skill evolution decisions.
"""

_EVOLVE_SOUL_MD = """\
You analyze agent session data and evolve reusable skills.
Be methodical: read all sessions, aggregate patterns, then make targeted
changes. Prefer conservative edits over rewrites. Skip when evidence is weak.
"""

_EVOLVE_IDENTITY_MD = """\
Skill Evolution Agent — SkillClaw
"""

_EVOLVE_USER_MD = """\
The operator is the SkillClaw evolve server. Follow EVOLVE_AGENTS.md.
"""


class AgentWorkspace:
    """Manages the filesystem workspace that the OpenClaw agent reads/writes."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.sessions_dir = self.root / "sessions"
        self.skills_dir = self.root / "skills"

    def reset(self) -> None:
        """Completely wipe and recreate the workspace (used in fresh mode)."""
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        logger.info("[AgentWorkspace] reset: wiped %s", self.root)

    def prepare(
        self,
        sessions: list[dict],
        existing_skills: dict[str, str | dict[str, bytes | bytearray | str]],
        manifest: dict[str, dict],
        agents_md: str,
        skill_registry_info: dict[str, Any] | None = None,
        feedback_bundle: list[dict[str, Any]] | None = None,
    ) -> None:
        """Populate the workspace with input data for the agent.

        Parameters
        ----------
        sessions:
            Raw session dicts drained from storage.
        existing_skills:
            ``{skill_name: bundle}`` for all current skills, where bundle is
            either a raw ``SKILL.md`` string or ``{rel_path: bytes}``.
        manifest:
            Current manifest dict ``{skill_name: metadata}``.
        agents_md:
            Full text of the AGENTS.md to write into the workspace.
        skill_registry_info:
            Optional registry metadata to expose to the agent.
        """
        # Clean sessions dir (always fresh input)
        if self.sessions_dir.exists():
            shutil.rmtree(self.sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Write session files (compact: metadata + trajectory + summary only)
        for s in sessions:
            sid = s.get("session_id", "unknown")
            compact = {
                "session_id": sid,
                "task_id": s.get("task_id", ""),
                "num_turns": s.get("num_turns", len(s.get("turns", []))),
                "aggregate": s.get("aggregate"),
                "_skills_referenced": sorted(s.get("_skills_referenced") or []),
                "_avg_prm": s.get("_avg_prm"),
                "_has_tool_errors": s.get("_has_tool_errors", False),
                "_trajectory": s.get("_trajectory", ""),
                "_summary": s.get("_summary", ""),
            }
            path = self.sessions_dir / f"{sid}.json"
            path.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

        # Write existing skills
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.skills_dir.iterdir()):
            if path.is_dir() and path.name not in existing_skills:
                shutil.rmtree(path)
        for name, content in existing_skills.items():
            skill_dir = self.skills_dir / name
            if isinstance(content, dict):
                write_skill_bundle(skill_dir, content, clean=True)
            else:
                write_skill_bundle(skill_dir, {"SKILL.md": content}, clean=True)

        # Write manifest
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Write skill registry info (read-only reference for the agent)
        if skill_registry_info:
            registry_path = self.root / "skill_registry.json"
            registry_path.write_text(
                json.dumps(skill_registry_info, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # Write optional validator-backed feedback bundle for this round.
        if feedback_bundle:
            feedback_dir = self.root / "feedback"
            feedback_dir.mkdir(parents=True, exist_ok=True)
            feedback_json_path = feedback_dir / "skill_feedback_bundle_latest.json"
            feedback_json_path.write_text(
                json.dumps(feedback_bundle, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (feedback_dir / "SUMMARY.md").write_text(
                _format_feedback_bundle_summary(feedback_bundle),
                encoding="utf-8",
            )
            (feedback_dir / "PLAYBOOK.md").write_text(
                _format_feedback_gate_playbook(feedback_bundle),
                encoding="utf-8",
            )
            agents_md = _augment_agents_md_with_feedback(
                agents_md,
                "feedback/skill_feedback_bundle_latest.json",
            )

        # Write EVOLVE_AGENTS.md (the detailed methodology the agent follows)
        agents_md_path = self.root / "EVOLVE_AGENTS.md"
        agents_md_path.write_text(agents_md, encoding="utf-8")

        # -----------------------------------------------------------
        # Pre-write OpenClaw bootstrap files.
        #
        # OpenClaw's ensureAgentWorkspace() creates these with
        # writeFileIfMissing (flag 'wx'), so it will NOT overwrite
        # files we write here. This lets us:
        #   - Replace AGENTS.md with a focused evolve-only version
        #     that directs the agent to read EVOLVE_AGENTS.md first.
        #   - Replace SOUL.md / IDENTITY.md / USER.md with minimal
        #     content to avoid wasting tokens on default templates.
        #   - Leave TOOLS.md untouched (agent needs tool descriptions).
        #   - Leave MEMORY.md / memory/ untouched (memory-core manages
        #     them; we want to preserve cross-round memory).
        # -----------------------------------------------------------
        bootstrap_files = {
            "AGENTS.md": _EVOLVE_AGENTS_MD,
            "SOUL.md": _EVOLVE_SOUL_MD,
            "IDENTITY.md": _EVOLVE_IDENTITY_MD,
            "USER.md": _EVOLVE_USER_MD,
        }
        for filename, content in bootstrap_files.items():
            fpath = self.root / filename
            fpath.write_text(content, encoding="utf-8")
            logger.debug("[AgentWorkspace] wrote bootstrap %s", filename)

        logger.info(
            "[AgentWorkspace] prepared: %d sessions, %d existing skills, bootstrap files written in %s",
            len(sessions),
            len(existing_skills),
            self.root,
        )

    def snapshot_skills(self) -> dict[str, str]:
        """Return ``{skill_name: tree_sha256}`` for all skills in the workspace."""
        snapshot: dict[str, str] = {}
        if not self.skills_dir.exists():
            return snapshot
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            bundle = read_skill_bundle(skill_dir)
            if "SKILL.md" in bundle:
                snapshot[skill_dir.name] = bundle_tree_sha256(bundle)
        return snapshot

    def collect_changes(
        self,
        before_snapshot: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Compare current skills against *before_snapshot* and return changed/new skills.

        Returns a list of dicts, each with:
        - ``name``: skill name
        - ``action``: ``"create"`` or ``"improve"``
        - ``skill``: parsed skill dict (name, description, content, ...)
        - ``raw_md``: the raw SKILL.md text
        - ``bundle_files``: full bundle contents ``{rel_path: bytes}``
        - ``tree_sha256``: directory-level fingerprint
        """
        after_snapshot = self.snapshot_skills()
        changes: list[dict[str, Any]] = []

        for name, after_sha in after_snapshot.items():
            before_sha = before_snapshot.get(name)
            if before_sha == after_sha:
                continue

            bundle_files = _normalize_text_bundle_newlines(read_skill_bundle(self.skills_dir / name))
            if "SKILL.md" not in bundle_files:
                logger.warning(
                    "[AgentWorkspace] changed skill '%s' is missing SKILL.md; skipping",
                    name,
                )
                continue

            raw_md = bundle_entrypoint_text(bundle_files)
            parsed = parse_skill_content(name, raw_md)

            action = "create" if before_sha is None else "improve"
            changes.append(
                {
                    "name": name,
                    "action": action,
                    "skill": parsed,
                    "raw_md": raw_md,
                    "bundle_files": bundle_files,
                    "tree_sha256": after_sha,
                }
            )
            logger.info(
                "[AgentWorkspace] detected %s: skill '%s' (sha %s -> %s)",
                action,
                name,
                (before_sha or "new")[:12],
                after_sha[:12],
            )

        deleted = set(before_snapshot) - set(after_snapshot)
        for name in sorted(deleted):
            logger.warning(
                "[AgentWorkspace] skill '%s' was deleted by agent — ignoring deletion",
                name,
            )

        return changes

    def cleanup_sessions(self) -> None:
        """Remove session files from the workspace after processing."""
        if self.sessions_dir.exists():
            shutil.rmtree(self.sessions_dir)
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
