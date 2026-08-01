# Skillspace

This directory is the unified parent path for SkillClaw's skill lifecycle.

- `source/`: Git-tracked baseline skills edited by humans.
- `live/`: runtime skill library loaded and auto-refreshed by SkillClaw.
- `state/`: runtime skill metadata such as `skill_stats.json`.
- `share/`: local shared storage for published skills, sessions, validation, and evolve artifacts.

The intended flow is:

1. Edit or review baseline skills in `source/`.
2. SkillClaw seeds `live/` from `source/` on startup.
3. Shared/evolved updates are pulled into `live/`.
4. Validated improvements can later be merged back into `source/` and committed.
