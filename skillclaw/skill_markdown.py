"""
Skill markdown rendering helpers shared by SkillClaw-side components.
"""

from __future__ import annotations

from typing import Any


def build_skill_md(skill: dict[str, Any]) -> str:
    """Render a skill dict into SKILL.md content with YAML frontmatter."""
    name = skill.get("name", "unknown")
    description = skill.get("description", "")
    category = skill.get("category", "general")
    content = skill.get("content", "")

    needs_quoting = any(c in str(description) for c in ":{}[],\"'#&*!|>%@`\n")
    if needs_quoting:
        escaped = str(description).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        desc_line = f'description: "{escaped}"'
    else:
        desc_line = f"description: {description}"

    fm_lines = [f"name: {name}", desc_line, f"category: {category}"]

    extra_fm = skill.get("extra_frontmatter")
    if isinstance(extra_fm, dict):
        for key, value in extra_fm.items():
            if value is None:
                continue
            fm_lines.append(f"{key}: {value}")

    frontmatter = "---\n" + "\n".join(fm_lines) + "\n---"
    return f"{frontmatter}\n\n{content}".rstrip() + "\n"
