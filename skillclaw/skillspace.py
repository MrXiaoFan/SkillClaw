from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLSPACE_ROOT = REPO_ROOT / "skillspace"
DEFAULT_SOURCE_DIR = DEFAULT_SKILLSPACE_ROOT / "source"
DEFAULT_LIVE_DIR = DEFAULT_SKILLSPACE_ROOT / "live"
DEFAULT_STATE_DIR = DEFAULT_SKILLSPACE_ROOT / "state"
DEFAULT_SHARE_DIR = DEFAULT_SKILLSPACE_ROOT / "share"
LEGACY_SOURCE_DIR = REPO_ROOT / "Skills"
LEGACY_SHARE_DIR = REPO_ROOT / ".local-share"


@dataclass(frozen=True)
class SkillspaceLayout:
    root: Path
    source_dir: Path
    live_dir: Path
    state_dir: Path
    share_dir: Path
    legacy_source_dir: Path
    legacy_share_dir: Path


DEFAULT_LAYOUT = SkillspaceLayout(
    root=DEFAULT_SKILLSPACE_ROOT,
    source_dir=DEFAULT_SOURCE_DIR,
    live_dir=DEFAULT_LIVE_DIR,
    state_dir=DEFAULT_STATE_DIR,
    share_dir=DEFAULT_SHARE_DIR,
    legacy_source_dir=LEGACY_SOURCE_DIR,
    legacy_share_dir=LEGACY_SHARE_DIR,
)


def default_layout() -> SkillspaceLayout:
    return DEFAULT_LAYOUT


def _normalized(path: str | Path) -> Path:
    return Path(str(path)).expanduser().resolve()


def is_repo_managed_skill_path(path: str | Path) -> bool:
    normalized = _normalized(path)
    layout = default_layout()
    return normalized in {
        layout.live_dir,
        layout.source_dir,
        layout.legacy_source_dir,
    }


def resolve_runtime_skills_dir(path: str | Path) -> str:
    normalized = _normalized(path)
    layout = default_layout()
    if normalized in {layout.source_dir, layout.legacy_source_dir, layout.live_dir}:
        return str(layout.live_dir)
    return str(normalized)


def resolve_source_skills_dir(path: str | Path) -> str:
    normalized = _normalized(path)
    layout = default_layout()
    if normalized in {layout.live_dir, layout.source_dir, layout.legacy_source_dir}:
        return str(layout.source_dir)
    return str(normalized)


def resolve_share_root(path: str | Path) -> str:
    normalized = _normalized(path)
    layout = default_layout()
    if normalized in {layout.share_dir, layout.legacy_share_dir}:
        return str(layout.share_dir)
    return str(normalized)


def is_skillspace_live_dir(path: str | Path) -> bool:
    return _normalized(path) == default_layout().live_dir


def is_skillspace_source_dir(path: str | Path) -> bool:
    return _normalized(path) == default_layout().source_dir


def is_skillspace_mutable_path(path: str | Path) -> bool:
    normalized = _normalized(path)
    layout = default_layout()
    mutable_roots = {
        layout.live_dir,
        layout.state_dir,
        layout.share_dir,
    }
    return any(root == normalized or root in normalized.parents for root in mutable_roots)


def skillspace_state_dir_for(path: str | Path) -> Path | None:
    normalized = _normalized(path)
    layout = default_layout()
    if normalized in {layout.live_dir, layout.source_dir, layout.legacy_source_dir}:
        return layout.state_dir
    return None


def ensure_skillspace_dirs() -> SkillspaceLayout:
    layout = default_layout()
    for path in (layout.root, layout.source_dir, layout.live_dir, layout.state_dir, layout.share_dir):
        path.mkdir(parents=True, exist_ok=True)
    return layout


def live_has_skills(path: str | Path | None = None) -> bool:
    live_dir = _normalized(path or default_layout().live_dir)
    if not live_dir.is_dir():
        return False
    for child in live_dir.iterdir():
        if child.is_dir() and (child / "SKILL.md").is_file():
            return True
    return False


def _replace_tree(source_dir: Path, target_dir: Path) -> None:
    if not source_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        for child in list(target_dir.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        return

    parent = target_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=".skillspace-stage-", dir=str(parent)))
    staged = staging_root / target_dir.name
    try:
        shutil.copytree(source_dir, staged)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        staged.replace(target_dir)
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)


def seed_live_from_source(*, log: logging.Logger | None = None) -> SkillspaceLayout:
    layout = ensure_skillspace_dirs()
    active_log = log or logger
    _replace_tree(layout.source_dir, layout.live_dir)
    active_log.info(
        "[Skillspace] refreshed runtime live skills from source: %s -> %s",
        layout.source_dir,
        layout.live_dir,
    )
    return layout
