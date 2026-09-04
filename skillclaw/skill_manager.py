# Adapted from MetaClaw
"""
Skill Manager for SkillClaw skill retrieval, injection, and local persistence.

Loads skills from a directory of skill subdirectories using the AgentSkills-
compatible format (shared with OpenClaw / Pi coding-agent):

    memory_data/skills/
        skill-name/
            SKILL.md           <- YAML frontmatter + markdown body
            scripts/           <- optional executable scripts
            references/        <- optional reference docs
            assets/            <- optional assets (templates, images, etc.)
        another-skill/
            SKILL.md

Each SKILL.md must have YAML frontmatter with at least ``name`` and
``description``::

    ---
    name: debug-systematically
    description: "Use when diagnosing a bug. Gather evidence before forming
      hypotheses.  NOT for: simple typo fixes."
    metadata:
      {
        "openclaw": { "emoji": "🔍" },
        "skillclaw": { "category": "coding" }
      }
    ---

    # Debug Systematically
    ...

Frontmatter fields
------------------
Required:
  name         lowercase-hyphenated slug
  description  rich trigger description — what, when to use, when NOT to use

Optional:
  metadata     nested dict; ``openclaw`` block for OpenClaw gating/install,
               ``skillclaw`` block for SkillClaw-specific fields (``category``)
  category     (legacy) — if present and ``metadata.skillclaw.category`` is
               absent, used as fallback; defaults to ``"general"``

Valid categories: general, coding, research, data_analysis, security,
                  communication, automation, agentic, productivity, common_mistakes
"""

import glob
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from typing import Any, Dict, Optional

import yaml

from . import runtime_state
from .skill_bundle import list_skill_bundle_paths

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_WORD_RE = re.compile(r"[a-zA-Z0-9_]{3,}|[\u4e00-\u9fff]{2,}")
_INLINE_QUERY_STOPWORDS = {
    "skill",
    "skills",
    "skillclaw",
    "server",
    "side",
    "server-side",
    "claude",
    "code",
    "local",
    "websearch",
    "json",
    "object",
    "current",
    "directory",
    "target",
    "program",
    "use",
    "using",
    "analyze",
    "analysis",
    "finish",
    "containing",
    "output",
    "already",
    "also",
    "and",
    "any",
    "are",
    "artifact",
    "artifacts",
    "assume",
    "at",
    "be",
    "been",
    "being",
    "blind",
    "both",
    "broad",
    "build",
    "but",
    "by",
    "call",
    "called",
    "calling",
    "calls",
    "can",
    "command",
    "commands",
    "confidence",
    "confirmation",
    "constraints",
    "continue",
    "continuing",
    "current",
    "demonstrated",
    "directory",
    "do",
    "does",
    "doing",
    "done",
    "evaluation",
    "exactly",
    "evidence",
    "exists",
    "experiment",
    "file",
    "files",
    "final",
    "for",
    "from",
    "function",
    "functions",
    "get",
    "gets",
    "getting",
    "grep",
    "have",
    "hidden",
    "identify",
    "if",
    "in",
    "input",
    "inspect",
    "instead",
    "into",
    "invoke",
    "is",
    "it",
    "its",
    "keys",
    "list",
    "may",
    "memory",
    "most",
    "neutral",
    "no",
    "normal",
    "not",
    "of",
    "one",
    "oracle",
    "other",
    "our",
    "out",
    "output",
    "outputs",
    "over",
    "plausible",
    "predicted_cves",
    "predicted_files",
    "predicted_functions",
    "present",
    "prefer",
    "produce",
    "project",
    "projects",
    "response",
    "responses",
    "root",
    "root_cause",
    "sample",
    "samples",
    "safety",
    "scan",
    "scans",
    "should",
    "single",
    "soon",
    "source",
    "stop",
    "supporting",
    "targeted",
    "task",
    "tasks",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "todowrite",
    "tool",
    "tools",
    "uncertain",
    "utility",
    "vulnerability",
    "vulnerabilities",
    "vuln",
    "vulnerable",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "working",
    "workflow",
    "workflows",
    "workspace",
    "you",
    "your",
}
_INLINE_DESCRIPTION_EXCLUSION_MARKERS = (
    " not for:",
    " strictly excluded:",
    " do not use for:",
    " excluded:",
)
# Matches conditional-exclusion clauses embedded inside the positive
# description, e.g. "it does NOT mention source code, crafted input,
# or any file-format parser."  Terms inside these clauses are negative
# (the skill explicitly says it should NOT be used when they appear),
# so they must be moved to the negative part to avoid false matches.
_NEGATIVE_CLAUSE_RE = re.compile(
    r"(?:it\s+)?does\s+not\s+(?:mention|perform|contain|include|require|handle|support)\b[^.]*\.",
    re.IGNORECASE,
)
_VULNERABILITY_TASK_TERMS = {
    "vulnerability",
    "vulnerabilities",
    "vuln",
    "cve",
    "cwe",
    "overflow",
    "overread",
    "read",
    "write",
    "oob",
    "parser",
    "firmware",
    "binary",
    "binaries",
    "elf",
    "source",
    "exploit",
    "exploitation",
    "漏洞",
    "越界",
    "溢出",
    "固件",
    "二进制",
    "源码",
}
_SOURCE_PARSER_TASK_TERMS = {
    "parser",
    "parsing",
    "state",
    "machine",
    "source",
    "code",
    "lookahead",
    "bounds",
    "bound",
    "boundary",
    "guard",
    "dominance",
    "fragment",
    "fragmentation",
    "header",
    "protocol",
    "packet",
    "tcpdump",
    "print",
    "frag6",
    "nd_tcheck",
    "cur",
    "end",
    "avail",
    "oob",
    "overread",
    "over",
    "read",
}
_SOURCE_PARSER_SKILL_TERMS = {
    "avail",
    "boundary",
    "bounds",
    "cur",
    "end",
    "fragment",
    "fragmentation",
    "guard",
    "header",
    "html",
    "lookahead",
    "machine",
    "nd_tcheck",
    "packet",
    "parser",
    "parsing",
    "protocol",
    "state",
    "xml",
}
_IDA_INTENT_TERMS = {
    "ida",
    "idalib",
    "hexrays",
    "hex-rays",
    "decompiler",
    "decompile",
    "headless",
    "i64",
}
_SSH_INTENT_TERMS = {
    "ssh",
    "password",
    "passwords",
    "credential",
    "credentials",
    "login",
    "paramiko",
    "sshpass",
    "recon",
    "reconnaissance",
}
_FIRMWARE_ROOTFS_TASK_TERMS = {
    "firmware",
    "rootfs",
    "extracted",
    "squashfs",
    "busybox",
    "router",
    "embedded",
    "iot",
    "cgi",
    "webvpn",
}
_BINARY_REVERSE_SKILL_TERMS = {
    "binary",
    "binaries",
    "cgis",
    "cgi",
    "decompiler",
    "decompile",
    "elf",
    "embedded",
    "firmware",
    "headless",
    "hexrays",
    "hex-rays",
    "ida",
    "idalib",
    "lua",
    "rootfs",
    "router",
    "shell",
    "triage",
}
_SKILLCLAW_META_MARKERS = (
    "available skills",
    "list skills",
    "skill count",
    "skill catalog",
    "server-side skill count",
    "/v1/skills",
    "settings.json",
    "proxy api",
    "proxy apis",
    "claude env",
    "skillclaw 配置",
    "skillclaw 服务端",
    "技能列表",
    "已有技能",
    "已有的 skill",
)


def _looks_like_skillclaw_meta_task(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in _SKILLCLAW_META_MARKERS)


def _looks_like_source_parser_task(query_terms: set[str]) -> bool:
    """Return True for source-level parser boundary-analysis tasks."""
    if not query_terms:
        return False
    source_hits = query_terms & _SOURCE_PARSER_TASK_TERMS
    if len(source_hits) < 2:
        return False
    has_parser_context = bool(
        query_terms & {"parser", "parsing", "fragment", "fragmentation", "protocol", "packet", "tcpdump"}
    )
    has_boundary_context = bool(
        query_terms & {"source", "code", "oob", "overread", "read", "bounds", "guard", "nd_tcheck"}
    )
    return has_parser_context and has_boundary_context


def _looks_like_firmware_rootfs_task(query_terms: set[str]) -> bool:
    return bool(query_terms & _FIRMWARE_ROOTFS_TASK_TERMS)


def _looks_like_binary_reverse_skill(skill_terms: set[str]) -> bool:
    return bool(skill_terms & _BINARY_REVERSE_SKILL_TERMS)


def _normalize_inline_query_text(task_description: str) -> str:
    text = str(task_description or "")
    marker = "\n\nExperiment execution constraints:"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text


def _inline_terms(text: str) -> set[str]:
    return set(_WORD_RE.findall(str(text or "").lower())) - _INLINE_QUERY_STOPWORDS


def _inline_negative_terms(text: str) -> set[str]:
    """Keep domain words from explicit exclusion clauses.

    The positive-query stopword list intentionally removes generic words such
    as ``source`` and ``code``. Those words still matter in phrases such as
    ``NOT for: source-code-only audits``, so exclusion matching uses a smaller
    marker-only filter instead.
    """
    marker_words = {"not", "for", "strictly", "excluded", "use", "do"}
    return set(_WORD_RE.findall(str(text or "").lower())) - marker_words


def _split_trigger_description(text: str) -> tuple[str, str]:
    lowered = str(text or "").lower()
    for marker in _INLINE_DESCRIPTION_EXCLUSION_MARKERS:
        idx = lowered.find(marker)
        if idx >= 0:
            positive = text[:idx]
            negative = text[idx + 1 :]
            break
    else:
        positive = str(text or "")
        negative = ""

    # Extract "does not mention/perform/etc." clauses from the positive
    # part and move them to the negative part.  Skills often phrase
    # exclusions as conditional requirements (e.g. "it does NOT mention
    # source code, crafted input"), and without this extraction those
    # terms would be treated as positive, causing false skill matches on
    # general vulnerability-analysis prompts.
    extracted = _NEGATIVE_CLAUSE_RE.findall(positive)
    if extracted:
        positive = _NEGATIVE_CLAUSE_RE.sub("", positive)
        negative = negative + " " + " ".join(extracted)

    return positive, negative

# ------------------------------------------------------------------ #
# Frontmatter parser                                                   #
# ------------------------------------------------------------------ #

_CORE_FM_KEYS = {"name", "description", "metadata", "category"}


def _parse_skill_md(path: str) -> Optional[Dict[str, Any]]:
    """Parse a SKILL.md file (AgentSkills / OpenClaw compatible format).

    Returns a dict with keys: name, description, category, content, and
    optionally metadata.  Extra frontmatter fields (e.g. ``homepage``,
    ``user-invocable``) are preserved verbatim so they survive round-trip
    writes.  Returns ``None`` if the file is missing required fields or
    has no frontmatter.

    Category resolution order:
      1. ``metadata.skillclaw.category``
      2. top-level ``category`` (legacy)
      3. ``"general"`` (default)
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        logger.warning("[SkillManager] could not read %s: %s", path, e)
        return None

    if not raw.startswith("---"):
        return None

    end_idx = raw.find("\n---", 3)
    if end_idx == -1:
        return None

    fm_text = raw[3:end_idx].strip()
    body = raw[end_idx + 4 :].strip()

    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        logger.warning("[SkillManager] invalid YAML frontmatter in %s", path)
        fm = {}

    if not isinstance(fm, dict):
        return None

    name = str(fm.get("name", "")).strip()
    description = str(fm.get("description", "")).strip()

    if not name or not description:
        logger.warning("[SkillManager] skipping %s — missing name or description", path)
        return None

    metadata = fm.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        metadata = None

    # Resolve category: metadata.skillclaw.category > top-level category > "general"
    category = "general"
    sc_meta = (metadata or {}).get("skillclaw", {})
    if isinstance(sc_meta, dict) and sc_meta.get("category"):
        category = str(sc_meta["category"]).strip()
    elif fm.get("category"):
        category = str(fm["category"]).strip()

    result: Dict[str, Any] = {
        "id": hashlib.sha256(name.encode()).hexdigest()[:12],
        "name": name,
        "description": description,
        "category": category,
        "content": body,
        "file_path": os.path.realpath(path),
    }
    if metadata:
        result["metadata"] = metadata

    # Preserve extra OpenClaw frontmatter fields (homepage, user-invocable, etc.)
    extra = {k: v for k, v in fm.items() if k not in _CORE_FM_KEYS}
    if extra:
        result["_extra_frontmatter"] = extra

    return result


# ------------------------------------------------------------------ #
# SkillManager                                                         #
# ------------------------------------------------------------------ #


class SkillManager:
    """Loads skills from a directory of AgentSkills / OpenClaw compatible
    skill folders.

    Each skill is a subdirectory containing a ``SKILL.md`` with YAML
    frontmatter (``name``, ``description``, optional ``metadata``) and a
    Markdown body.

    Supports two retrieval modes:
      * ``"template"`` – flat effectiveness-ranked retrieval, zero latency
      * ``"embedding"`` – cosine similarity via SentenceTransformer
    """

    def __init__(
        self,
        skills_dir: str,
        public_skill_root: str = "",
        retrieval_mode: str = "template",
        embedding_model_path: Optional[str] = None,
    ):
        if retrieval_mode not in ("template", "embedding"):
            raise ValueError(f"retrieval_mode must be 'template' or 'embedding', got '{retrieval_mode}'")
        if not os.path.isdir(skills_dir):
            raise FileNotFoundError(f"Skills directory not found: {skills_dir}")

        self._skills_dir = skills_dir
        self._public_skill_root = public_skill_root.strip()
        self.retrieval_mode = retrieval_mode
        self.embedding_model_path = embedding_model_path or "Qwen/Qwen3-Embedding-0.6B"

        self._embedding_model = None
        self._skill_embeddings_cache: Optional[Dict] = None

        # Monotonically-increasing counter. Incremented whenever the local
        # skill library changes so callers can drop stale snapshots.
        self.generation: int = 0

        self.skills = self._load_skills()
        self._skills_fingerprint = self._compute_skills_fingerprint()
        self._stats = self._load_stats()
        self._stats_dirty = 0

        counts = self._category_counts()
        logger.info(
            "[SkillManager] loaded %d skills from %s | mode=%s | categories=%s",
            len(self.skills.get("all_skills", [])),
            skills_dir,
            retrieval_mode,
            dict(counts),
        )

        if retrieval_mode == "embedding":
            self._compute_skill_embeddings()

    # ------------------------------------------------------------------ #
    # Skill stats tracking                                                 #
    # ------------------------------------------------------------------ #

    def _stats_path(self) -> str:
        return str(runtime_state.skill_stats_path(self._skills_dir))

    def _legacy_stats_path(self) -> str:
        return str(runtime_state.legacy_skill_stats_path(self._skills_dir))

    def _load_stats(self) -> Dict[str, Dict[str, Any]]:
        path = self._stats_path()
        legacy_path = self._legacy_stats_path()
        candidate = path if os.path.exists(path) else legacy_path
        if not os.path.exists(candidate):
            return {}
        try:
            with open(candidate, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[SkillManager] failed to load stats: %s", e)
            return {}

    def _save_stats(self) -> None:
        try:
            path = self._stats_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("[SkillManager] failed to save stats: %s", e)

    def _maybe_flush_stats(self) -> None:
        """Persist stats every 10 mutations to avoid excessive I/O."""
        self._stats_dirty += 1
        if self._stats_dirty >= 10:
            self._save_stats()
            self._stats_dirty = 0

    def record_injection(self, skill_names: list[str]) -> None:
        """Record that these skills were injected into a request."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for name in skill_names:
            entry = self._stats.setdefault(
                name,
                {
                    "inject_count": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "last_injected_at": "",
                    "effectiveness": 0.5,
                },
            )
            entry["inject_count"] += 1
            entry["last_injected_at"] = now
        self._maybe_flush_stats()

    def record_feedback(self, skill_names: list[str], score: float) -> None:
        """Record PRM feedback for skills that were injected in a turn."""
        for name in skill_names:
            entry = self._stats.get(name)
            if entry is None:
                continue
            if score > 0:
                entry["positive_count"] += 1
            elif score < 0:
                entry["negative_count"] += 1
            else:
                entry["neutral_count"] += 1
            total = entry["inject_count"]
            entry["effectiveness"] = entry["positive_count"] / total if total > 0 else 0.5
        self._maybe_flush_stats()

    def get_effectiveness(self, skill_name: str) -> float:
        """Return the effectiveness score for a skill (default 0.5 for unknown)."""
        entry = self._stats.get(skill_name)
        if entry is None:
            return 0.5
        return entry.get("effectiveness", 0.5)

    def get_stats_summary(self) -> Dict[str, Dict[str, Any]]:
        """Return a copy of the full stats dict."""
        return dict(self._stats)

    # ------------------------------------------------------------------ #
    # Loading                                                              #
    # ------------------------------------------------------------------ #

    def _load_skills(self) -> Dict[str, Any]:
        """Scan skills_dir for */SKILL.md files and parse each into a flat collection."""
        result: Dict[str, Any] = {"all_skills": []}

        paths = self._skill_md_paths()
        if not paths:
            logger.warning("[SkillManager] no SKILL.md files found in %s", self._skills_dir)
            return result

        for path in paths:
            skill = _parse_skill_md(path)
            if skill is None:
                continue
            result["all_skills"].append(skill)

        return result

    def _skill_md_paths(self) -> list[str]:
        if self._is_hermes_skill_root():
            pattern = os.path.join(self._skills_dir, "**", "SKILL.md")
            return sorted(glob.glob(pattern, recursive=True))
        pattern = os.path.join(self._skills_dir, "*", "SKILL.md")
        return sorted(glob.glob(pattern))

    def _compute_skills_fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        fingerprint: list[tuple[str, int, int]] = []
        for path in self._skill_md_paths():
            try:
                stat = os.stat(path)
            except OSError:
                continue
            fingerprint.append(
                (
                    os.path.realpath(path),
                    int(stat.st_mtime_ns),
                    int(stat.st_size),
                )
            )
        return tuple(fingerprint)

    def _is_hermes_skill_root(self) -> bool:
        return os.path.realpath(self._skills_dir) == os.path.realpath(
            os.path.join(os.path.expanduser("~"), ".hermes", "skills")
        )

    def _skill_dir_path(self, skill: dict) -> str:
        name = str(skill.get("name", "unknown") or "unknown").strip()
        category = str(skill.get("category", "general") or "general").strip()
        if self._is_hermes_skill_root() and category and category != "general":
            return os.path.join(self._skills_dir, category, name)
        return os.path.join(self._skills_dir, name)

    def _skill_md_path(self, skill: dict) -> str:
        return os.path.join(self._skill_dir_path(skill), "SKILL.md")

    def reload(self) -> None:
        """Re-scan the skills directory and rebuild the internal skill bank."""
        self._save_stats()
        self.skills = self._load_skills()
        self._skills_fingerprint = self._compute_skills_fingerprint()
        self._stats = self._load_stats()
        self._skill_embeddings_cache = None
        if self.retrieval_mode == "embedding":
            self._compute_skill_embeddings()
        logger.info("[SkillManager] reloaded skills from %s", self._skills_dir)

    def refresh_if_changed(self) -> bool:
        """Reload skills if the on-disk skill library changed externally."""
        current = self._compute_skills_fingerprint()
        if current == self._skills_fingerprint:
            return False
        self.reload()
        self.generation += 1
        logger.info("[SkillManager] detected local skill changes; refreshed library")
        return True

    # ------------------------------------------------------------------ #
    # Embedding helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embedding retrieval. "
                    "Install with: pip install sentence-transformers"
                )
            logger.info("[SkillManager] loading embedding model: %s", self.embedding_model_path)
            self._embedding_model = SentenceTransformer(self.embedding_model_path)
        return self._embedding_model

    @staticmethod
    def _skill_to_text(skill: Dict[str, Any]) -> str:
        parts = [
            skill.get("name", "").strip(),
            skill.get("description", "").strip(),
        ]
        content = skill.get("content", "").strip()
        if content:
            parts.append(content[:200])
        return ". ".join(p for p in parts if p)

    def _compute_skill_embeddings(self) -> Dict:
        if self._skill_embeddings_cache is not None:
            return self._skill_embeddings_cache

        import numpy as np

        all_items = list(self.skills.get("all_skills", []))
        texts = [self._skill_to_text(skill) for skill in all_items]

        if not texts:
            self._skill_embeddings_cache = {
                "items": [],
                "embeddings": np.zeros((0, 0), dtype=float),
            }
            return self._skill_embeddings_cache

        model = self._get_embedding_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        self._skill_embeddings_cache = {
            "items": all_items,
            "embeddings": embeddings,
        }
        logger.info("[SkillManager] cached %d skill embeddings", len(all_items))
        return self._skill_embeddings_cache

    def _weighted_score(self, similarity: float, skill_name: str) -> float:
        """Combine embedding similarity with effectiveness for ranking."""
        eff = self.get_effectiveness(skill_name)
        return similarity * (0.3 + 0.7 * eff)

    def _deduplicate_by_embedding(
        self, indices: list[int], cache: dict, top_k: int, threshold: float = 0.9
    ) -> list[int]:
        """Remove near-duplicate skills from candidate list, keeping the one
        with higher weighted score. Fills freed slots with next candidates."""
        if not indices:
            return []
        embs = cache["embeddings"]
        kept: list[int] = []
        for idx in indices:
            is_dup = False
            for kept_idx in kept:
                sim = float(embs[idx] @ embs[kept_idx])
                if sim > threshold:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(idx)
            if len(kept) >= top_k:
                break
        return kept

    def _embedding_retrieve(self, task_description: str, top_k: int) -> list[dict]:
        cache = self._compute_skill_embeddings()
        if not cache["items"]:
            return []
        model = self._get_embedding_model()
        query_emb = model.encode(
            [task_description],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )[0]

        sims = cache["embeddings"] @ query_emb
        items = cache["items"]

        ranked = sorted(
            range(len(sims)),
            key=lambda i: self._weighted_score(float(sims[i]), items[i].get("name", "")),
            reverse=True,
        )
        candidate_indices = ranked[: max(top_k * 3, top_k)]
        kept = self._deduplicate_by_embedding(candidate_indices, cache, top_k)
        return [items[i] for i in kept]

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def retrieve(self, task_description: str, top_k: int = 6) -> list[dict]:
        """Retrieve relevant skills for *task_description*.

        In embedding mode, skills are ranked by similarity * effectiveness and
        deduplicated by embedding similarity. In template mode, all skills are
        sorted by effectiveness without any category-specific routing.
        """
        if self.retrieval_mode == "embedding":
            return self._embedding_retrieve(task_description, top_k)

        all_skills = list(self.skills.get("all_skills", []))
        all_skills_sorted = sorted(
            all_skills,
            key=lambda s: self.get_effectiveness(s.get("name", "")),
            reverse=True,
        )
        return all_skills_sorted[:top_k]

    # ------------------------------------------------------------------ #
    # Model-side skill catalog (OpenClaw-compatible lazy loading)           #
    # ------------------------------------------------------------------ #

    def get_all_skills(self) -> list[dict]:
        """Return a flat list of ALL loaded skills eligible for model invocation.

        Skills with ``disable-model-invocation: true`` in their frontmatter
        are filtered out (matching OpenClaw behaviour).
        """
        return [
            s
            for s in self.skills.get("all_skills", [])
            if not s.get("_extra_frontmatter", {}).get("disable-model-invocation", False)
        ]

    def get_skill_path_map(self) -> Dict[str, Dict[str, str]]:
        """Return a mapping from bundle file path → {skill_id, skill_name}.

        Used by the server to resolve which skill a ``read`` tool call targets.
        """
        path_map: Dict[str, Dict[str, str]] = {}

        def add_path(path: str, skill: dict) -> None:
            if path:
                path_map[path] = {
                    "skill_id": skill.get("id", ""),
                    "skill_name": skill.get("name", ""),
                }
                normalized = os.path.realpath(path)
                path_map[normalized] = path_map[path]

        for s in self.get_all_skills():
            skill_dir = os.path.dirname(str(s.get("file_path", "") or ""))
            bundle_paths = list_skill_bundle_paths(skill_dir) if skill_dir else []
            bundle_paths = bundle_paths or ["SKILL.md"]
            public_dir = os.path.dirname(self._public_skill_path(s)) if self._public_skill_path(s) else ""
            for rel_path in bundle_paths:
                if skill_dir:
                    add_path(os.path.join(skill_dir, rel_path), s)
                if public_dir:
                    if "/" in public_dir and "\\" not in public_dir:
                        add_path("/".join([public_dir.rstrip("/"), rel_path.replace("\\", "/")]), s)
                    else:
                        add_path(os.path.join(public_dir, rel_path), s)
        return path_map

    def _public_skill_path(self, skill: dict) -> str:
        if not self._public_skill_root:
            return ""
        name = str(skill.get("name", "")).strip()
        if not name:
            return ""
        if "/" in self._public_skill_root and "\\" not in self._public_skill_root:
            return "/".join([self._public_skill_root.rstrip("/"), name, "SKILL.md"])
        return os.path.join(self._public_skill_root, name, "SKILL.md")

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters (matching OpenClaw's escapeXml)."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def format_skills_for_prompt(self, skills: list[dict]) -> str:
        """Build the *full* ``<available_skills>`` XML catalog.

        Output matches ``formatSkillsForPrompt`` from
        ``@mariozechner/pi-coding-agent`` (used by OpenClaw): preamble text
        followed by ``<available_skills>`` with ``<name>``, ``<description>``,
        and ``<location>`` per skill.
        """
        if not skills:
            return ""
        escape = SkillManager._escape_xml
        lines = [
            "\n\nThe following skills provide specialized instructions for specific tasks.",
            "Use the read tool to load a skill's file when the task matches its description.",
            "When a skill file references a relative path, resolve it against the skill "
            "directory (parent of SKILL.md / dirname of the path) and use that absolute "
            "path in tool commands.",
            "",
            "<available_skills>",
        ]
        for skill in skills:
            lines.append("  <skill>")
            lines.append(f"    <name>{escape(skill.get('name', ''))}</name>")
            lines.append(f"    <description>{escape(skill.get('description', ''))}</description>")
            lines.append(
                f"    <location>{escape(self._public_skill_path(skill) or skill.get('file_path', ''))}</location>"
            )
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def format_skills_compact(self, skills: list[dict]) -> str:
        """Build the *compact* ``<available_skills>`` XML catalog.

        Omits ``<description>`` to save tokens.  Matches OpenClaw's
        ``formatSkillsCompact``.
        """
        if not skills:
            return ""
        escape = SkillManager._escape_xml
        lines = [
            "\n\nThe following skills provide specialized instructions for specific tasks.",
            "Use the read tool to load a skill's file when the task matches its name.",
            "When a skill file references a relative path, resolve it against the skill "
            "directory (parent of SKILL.md / dirname of the path) and use that absolute "
            "path in tool commands.",
            "",
            "<available_skills>",
        ]
        for skill in skills:
            lines.append("  <skill>")
            lines.append(f"    <name>{escape(skill.get('name', ''))}</name>")
            lines.append(
                f"    <location>{escape(self._public_skill_path(skill) or skill.get('file_path', ''))}</location>"
            )
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    @staticmethod
    def build_skills_section(
        skills_prompt: str,
        read_tool_name: str = "read",
    ) -> str:
        """Wrap a skills catalog string with the ``## Skills (mandatory)``
        instruction block.

        Matches OpenClaw's ``buildSkillsSection`` in ``system-prompt.ts``.
        """
        trimmed = skills_prompt.strip()
        if not trimmed:
            return ""
        return "\n".join(
            [
                "## Skills (mandatory)",
                "SkillClaw skills are server-side guidance, not client-local Claude Code skills.",
                "- Do not call the client's local `Skill(...)` tool for SkillClaw skills unless the user explicitly asks for Claude Code local skills.",
                "Before replying: scan <available_skills> <description> entries.",
                "- If the user explicitly names a skill, select that exact skill and read its "
                "SKILL.md at <location> before any project search or analysis.",
                f"- If exactly one skill clearly applies: read its SKILL.md at "
                f"<location> with `{read_tool_name}`, then follow it.",
                "- If multiple could apply: choose the most specific one, then read/follow it.",
                "- If none clearly apply: do not read any SKILL.md.",
                "- Do not search the current project for SKILL.md; use the absolute <location> "
                "from <available_skills>.",
                "Constraints: never read more than one skill up front; only read after selecting.",
                "- When a skill drives external API writes, assume rate limits: prefer fewer "
                "larger writes, avoid tight one-item loops, serialize bursts when possible, "
                "and respect 429/Retry-After.",
                trimmed,
                "",
            ]
        )

    def build_injection_prompt(
        self,
        max_chars: int = 30_000,
        read_tool_name: str = "read",
    ) -> str:
        """One-call helper: catalog all skills and wrap with instructions.

        Uses the full format (name + description + location) when the catalog
        fits within *max_chars*; falls back to compact format (name + location)
        otherwise.  Returns the empty string when no skills are loaded.
        """
        skills = self.get_all_skills()
        if not skills:
            return ""
        full_prompt = self.format_skills_for_prompt(skills)
        if len(full_prompt) <= max_chars:
            catalog = full_prompt
        else:
            catalog = self.format_skills_compact(skills)
        return self.build_skills_section(catalog, read_tool_name)

    def select_skills_for_inline(self, task_description: str, top_k: int = 3) -> list[dict]:
        """Choose a small set of skills whose full contents should be injected.

        Local enhancement: this path is the bridge from SkillClaw's server-side
        skill bank to remote Claude Code clients that only connect by API key.

        Exact skill-name mentions are always prioritized.  Remaining slots use
        the configured retrieval strategy so key-only remote clients can benefit
        from server-side skills without reading files from their filesystem.
        """
        all_skills = self.get_all_skills()
        if not all_skills:
            return []

        text = str(task_description or "").lower()
        selected: list[dict] = []
        seen: set[str] = set()

        for skill in all_skills:
            name = str(skill.get("name") or "").strip()
            if name and name.lower() in text:
                selected.append(skill)
                seen.add(name)

        if len(selected) < max(1, top_k):
            if self.retrieval_mode == "embedding":
                candidates = self.retrieve(task_description, top_k=max(1, top_k) * 2)
            else:
                candidates = self._keyword_retrieve_for_inline(task_description, top_k=max(1, top_k) * 2)
            for skill in candidates:
                name = str(skill.get("name") or "").strip()
                if name and name not in seen:
                    selected.append(skill)
                    seen.add(name)
                if len(selected) >= max(1, top_k):
                    break

        return selected[: max(1, top_k)]

    def _keyword_retrieve_for_inline(self, task_description: str, top_k: int = 6) -> list[dict]:
        """Rank skills by lightweight lexical overlap for inline injection."""
        task_text = _normalize_inline_query_text(str(task_description or ""))
        task_terms_all = set(_WORD_RE.findall(task_text.lower()))
        query_terms = _inline_terms(task_text)
        if not query_terms:
            return self.retrieve(task_description, top_k=top_k)
        is_vulnerability_task = bool(task_terms_all & _VULNERABILITY_TASK_TERMS)
        is_skillclaw_meta_task = _looks_like_skillclaw_meta_task(task_text.lower())
        is_source_parser_task = _looks_like_source_parser_task(task_terms_all)
        is_firmware_rootfs_task = _looks_like_firmware_rootfs_task(task_terms_all)
        has_ida_intent = bool(task_terms_all & _IDA_INTENT_TERMS)
        ssh_intent_hits = task_terms_all & _SSH_INTENT_TERMS

        scored: list[tuple[float, dict]] = []
        for skill in self.get_all_skills():
            name = str(skill.get("name") or "")
            # Local enhancement: remote Claude Code prompts often contain
            # words like "SkillClaw server-side skills" as plumbing language.
            # For vulnerability-analysis tasks, do not let SkillClaw
            # self-inspection skills consume inline top-k slots.  A mixed
            # prompt can mention the API proxy while still being a real target
            # analysis task, so metadata skills are only eligible for explicit
            # SkillClaw-management requests.
            if name.startswith("skillclaw-") and (is_vulnerability_task or not is_skillclaw_meta_task):
                continue
            if is_source_parser_task and name.startswith(("ida-", "idalib-")) and not has_ida_intent:
                continue
            if is_source_parser_task and not is_firmware_rootfs_task and name in {
                "vuln-hunting",
                "vuln-hunting-claw",
                "verify-rootfs-full-enumeration",
                "elf-cwe120-firmware-triage",
            }:
                continue
            if name == "ssh-password-recon-workflow" and is_vulnerability_task and len(ssh_intent_hits) < 2:
                continue
            description = str(skill.get("description") or "")
            positive_desc, negative_desc = _split_trigger_description(description)
            name_terms = _inline_terms(name)
            desc_terms = _inline_terms(positive_desc)
            category_terms = _inline_terms(str(skill.get("category") or ""))
            negative_terms = _inline_terms(negative_desc)
            positive_skill_terms = name_terms | desc_terms
            content_terms: set[str] = set()
            if is_skillclaw_meta_task:
                content_terms = _inline_terms(str(skill.get("content") or "")[:1200])
            if (
                is_source_parser_task
                and not is_firmware_rootfs_task
                and _looks_like_binary_reverse_skill(positive_skill_terms)
                and not (positive_skill_terms & _SOURCE_PARSER_SKILL_TERMS)
            ):
                continue

            name_overlap = query_terms & name_terms
            desc_overlap = query_terms & desc_terms
            category_overlap = query_terms & category_terms
            negative_overlap = task_terms_all & _inline_negative_terms(negative_desc)
            # An explicit exclusion marker is a hard veto when at least one
            # meaningful query term matches it. Requiring several overlaps
            # lets clearly excluded tasks through when descriptions use short
            # domain phrases such as "NOT for: GIF image decoders".
            if negative_overlap:
                continue
            content_overlap = query_terms & content_terms
            score = (
                len(name_overlap) * 4.0
                + len(desc_overlap) * 2.0
                + len(category_overlap) * 0.5
                + len(content_overlap) * 1.0
                - len(negative_overlap) * 1.5
            )
            if score <= 0:
                continue
            score += self.get_effectiveness(name) * 0.25
            # Local enhancement: prefer source-level parser boundary workflows
            # for tasks that ask about parser/header/OOB bugs in source trees.
            # Generic ELF/IDA triage skills are useful fallback guidance, but
            # they should not outrank a source parser skill unless the user
            # explicitly asks for IDA/headless/decompiler analysis.
            if is_source_parser_task:
                if name == "source-parser-state-machine-oob":
                    score += 8.0
                elif name.startswith(("ida-", "idalib-")) and not has_ida_intent:
                    score -= 4.0
                elif "cwe120" in name and not (query_terms & {"cwe", "cwe120", "overflow"}):
                    score -= 1.5
            scored.append((score, skill))

        if not scored:
            # Fallback: when lexical scoring produces no positive matches,
            # return the top-k skills by effectiveness so the model still
            # receives guidance.  This prevents the "no skill selected"
            # failure mode where a vulnerability-analysis task gets zero
            # skills because keyword overlap was zero (e.g., the query uses
            # different terminology than skill descriptions, or negative
            # trigger terms filtered out all candidates).
            fallback_pool = []
            for skill in self.get_all_skills():
                name = str(skill.get("name") or "")
                if name.startswith("skillclaw-") and (is_vulnerability_task or not is_skillclaw_meta_task):
                    continue
                # Respect explicit negative exclusion clauses in fallback too
                fb_desc = str(skill.get("description") or "")
                _, fb_neg = _split_trigger_description(fb_desc)
                if task_terms_all & _inline_negative_terms(fb_neg):
                    continue
                fallback_pool.append(skill)
            if not fallback_pool:
                return []
            fallback_pool.sort(
                key=lambda s: self.get_effectiveness(str(s.get("name") or "")),
                reverse=True,
            )
            return fallback_pool[:top_k]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]

    def format_inline_skills_for_prompt(self, skills: list[dict], max_chars: int = 30_000, include_catalog: bool = True) -> str:
        """Build an inline skill prompt that includes SKILL.md bodies."""
        if not skills:
            return ""

        escape = SkillManager._escape_xml
        lines = [
            "## Skills (server-loaded)",
            "SkillClaw server-side skills are different from the client's local Claude Code skills.",
            "Do not call the client's local `Skill(...)` tool for these SkillClaw skills; they are already injected as text.",
            "If a client-local Skill tool reports 'Unknown skill', ignore that local-tool error and continue with the injected SkillClaw instructions.",
        ]
        if include_catalog:
            lines.append("If the user asks which skills are available on the SkillClaw/LLM/server side, answer from <available_server_skills>.")
            lines.append("")
            lines.append("<available_server_skills>")
            for skill in self.get_all_skills():
                lines.append("  <skill>")
                lines.append(f"    <name>{escape(str(skill.get('name') or ''))}</name>")
                lines.append(f"    <description>{escape(str(skill.get('description') or ''))}</description>")
                lines.append("  </skill>")
            lines.append("</available_server_skills>")
        lines.extend(
            [
                "",
                "## Loaded Skill Instructions",
            ]
        )
        lines.extend([
            "The SkillClaw server has already loaded the following skill files.",
            "Use these instructions directly; do not search for or read SKILL.md from the remote filesystem.",
            "Do not invoke Claude Code's local Skill tool to initialize these skills.",
            "Treat these loaded skills as the primary source of task guidance.",
            "Do not use WebSearch or external web browsing as the first step when a loaded skill applies, unless the user explicitly asks for current/latest public information.",
            "Begin by applying the loaded skill workflow to the user's workspace, files, firmware, binaries, logs, or target environment.",
            "If multiple skills are present, follow the most specific applicable skill.",
            "",
            "<loaded_skills>",
        ])
        current_len = sum(len(line) + 1 for line in lines)
        included = 0

        for skill in skills:
            name = str(skill.get("name") or "")
            description = str(skill.get("description") or "")
            content = str(skill.get("content") or "")
            block_prefix = [
                "  <skill>",
                f"    <name>{escape(name)}</name>",
                f"    <description>{escape(description)}</description>",
                "    <content>",
            ]
            block_suffix = [
                "    </content>",
                "  </skill>",
            ]
            reserved = sum(len(line) + 1 for line in block_prefix + block_suffix) + len("</loaded_skills>\n")
            available = max_chars - current_len - reserved
            if available <= 200 and included:
                break
            if available <= 200:
                available = max(0, available)
            body = content
            if len(body) > available:
                body = body[: max(0, available)] + "\n[Skill content truncated by SkillClaw prompt budget.]"

            block = block_prefix + [escape(body)] + block_suffix
            block_len = sum(len(line) + 1 for line in block)
            if current_len + block_len + len("</loaded_skills>\n") > max_chars and included:
                break
            lines.extend(block)
            current_len += block_len
            included += 1

        lines.append("</loaded_skills>")
        return "\n".join(lines) if included else ""

    def build_inline_injection_prompt(
        self,
        task_description: str,
        max_chars: int = 30_000,
        top_k: int = 3,
    ) -> tuple[str, list[str]]:
        """Return server-loaded skill content and the selected skill names."""
        selected = self.select_skills_for_inline(task_description, top_k=top_k)
        prompt = self.format_inline_skills_for_prompt(selected, max_chars=max_chars)
        names = [str(s.get("name") or "unknown_skill") for s in selected if isinstance(s, dict)]
        return prompt, names

    def _remove_skill_from_memory(self, name: str) -> None:
        """Remove a skill from in-memory structures (not from disk)."""
        self.skills["all_skills"] = [s for s in self.skills.get("all_skills", []) if s.get("name") != name]

    def add_skill(self, skill: dict) -> bool:
        """
        Add a new skill to the in-memory bank and write its SKILL.md file.

        Returns True if the skill was added, False if it already exists
        (unless ``skill["_replace"]`` is truthy, in which case the old
        version is overwritten).
        """
        name = skill.get("name", "").strip()
        if not name:
            logger.warning("[SkillManager] add_skill called with missing name")
            return False
        if not _SAFE_NAME_RE.match(name):
            logger.warning("[SkillManager] rejected invalid skill name: %s", name)
            return False

        existing = self._get_all_skill_names()
        if name in existing:
            if skill.get("_replace"):
                self._remove_skill_from_memory(name)
                logger.info("[SkillManager] replacing existing skill: %s", name)
            else:
                logger.info("[SkillManager] skipping duplicate skill: %s", name)
                return False

        clean_skill = {k: v for k, v in skill.items() if not k.startswith("_") or k == "_extra_frontmatter"}
        if "id" not in clean_skill:
            clean_skill["id"] = hashlib.sha256(name.encode()).hexdigest()[:12]
        if "file_path" not in clean_skill:
            clean_skill["file_path"] = os.path.realpath(self._skill_md_path(clean_skill))
        clean_skill["category"] = str(clean_skill.get("category", "general") or "general").strip()
        self.skills.setdefault("all_skills", []).append(clean_skill)

        self._skill_embeddings_cache = None
        self._write_skill_md(clean_skill)
        self._skills_fingerprint = self._compute_skills_fingerprint()
        logger.info("[SkillManager] added skill: %s", name)
        return True

    def add_skills(self, new_skills: list[dict], category: str = "general") -> int:
        """Add multiple skills; returns count actually added.

        Increments ``self.generation`` when at least one skill is successfully
        added, signalling callers that the local skill library changed.
        """
        added = 0
        for skill in new_skills:
            if "category" not in skill:
                skill = {**skill, "category": category}
            if self.add_skill(skill):
                added += 1
        if added > 0:
            self.generation += 1
        return added

    @staticmethod
    def _format_frontmatter(skill: dict) -> str:
        """Serialize skill frontmatter as YAML, OpenClaw-compatible.

        Produces output like::

            name: my-skill
            description: "Rich description with: colons and special chars."
            homepage: https://example.com
            metadata:
              {
                "openclaw": { "emoji": "🔧" },
                "skillclaw": { "category": "coding" }
              }

        Extra frontmatter fields (``homepage``, ``user-invocable``, etc.)
        are written between ``description`` and ``metadata`` to match the
        OpenClaw SKILL.md convention.
        """
        lines: list[str] = []
        name = skill.get("name", "unknown")
        description = skill.get("description", "")
        metadata = skill.get("metadata")
        extra_fm = skill.get("_extra_frontmatter", {})

        lines.append(f"name: {name}")

        needs_quoting = any(c in description for c in ":{}[],\"'#&*!|>%@`\n")
        if needs_quoting:
            escaped = description.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'description: "{escaped}"')
        else:
            lines.append(f"description: {description}")

        # Write extra OpenClaw frontmatter fields (homepage, user-invocable, etc.)
        for key, value in extra_fm.items():
            if key.startswith("_"):
                continue
            dumped = yaml.dump(
                {key: value},
                default_flow_style=False,
                allow_unicode=True,
                width=10000,
            ).strip()
            lines.append(dumped)

        if metadata and isinstance(metadata, dict):
            json_str = json.dumps(metadata, ensure_ascii=False, indent=2)
            indented = "\n".join("  " + ln for ln in json_str.splitlines())
            lines.append(f"metadata:\n{indented}")

        return "\n".join(lines)

    def _write_skill_md(self, skill: dict) -> None:
        """Persist a single skill to its SKILL.md file (AgentSkills / OpenClaw
        compatible format).

        Category is stored in ``metadata.skillclaw.category`` (not as a bare
        top-level frontmatter field) so the output is fully OpenClaw-compatible.
        Extra frontmatter fields (e.g. ``homepage``) that were parsed from an
        existing SKILL.md are preserved in the output.
        """
        name = skill.get("name", "unknown")
        skill_dir = self._skill_dir_path(skill)
        canonical = os.path.realpath(skill_dir)
        if not canonical.startswith(os.path.realpath(self._skills_dir) + os.sep):
            logger.warning("[SkillManager] blocked path traversal in skill name: %s", name)
            return
        os.makedirs(skill_dir, exist_ok=True)
        filepath = self._skill_md_path(skill)

        category = skill.get("category", "general")
        content = skill.get("content", "")
        metadata = dict(skill.get("metadata") or {})

        if category and category != "general":
            metadata.setdefault("skillclaw", {})["category"] = category

        write_skill: Dict[str, Any] = {
            "name": name,
            "description": skill.get("description", ""),
        }
        extra_fm = skill.get("_extra_frontmatter")
        if extra_fm:
            write_skill["_extra_frontmatter"] = extra_fm
        if metadata:
            write_skill["metadata"] = metadata

        fm_text = self._format_frontmatter(write_skill)
        text = f"---\n{fm_text}\n---\n\n{content}\n"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            skill["file_path"] = os.path.realpath(filepath)
            logger.info("[SkillManager] wrote skill file: %s", filepath)
        except OSError as e:
            logger.warning("[SkillManager] could not write %s: %s", filepath, e)

    def save(self, path: Optional[str] = None) -> None:
        """
        Persist all in-memory skills back to .md files.

        ``path`` is ignored (kept for backward compatibility); files are always
        written to skills_dir.
        """
        all_skills = list(self.skills.get("all_skills", []))
        for skill in all_skills:
            self._write_skill_md(skill)
        self._skills_fingerprint = self._compute_skills_fingerprint()
        logger.info("[SkillManager] saved %d skills to %s", len(all_skills), self._skills_dir)

    def _get_all_skill_names(self) -> set:
        return {str(s.get("name")) for s in self.skills.get("all_skills", []) if s.get("name")}

    def _category_counts(self) -> Counter:
        return Counter(str(s.get("category") or "general") for s in self.skills.get("all_skills", []))

    def get_skill_count(self) -> dict:
        return {
            "total": len(self.skills.get("all_skills", [])),
            "by_category": dict(self._category_counts()),
        }
