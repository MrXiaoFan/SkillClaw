"""
CLI entry point — ``python -m evolve_server``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

from .core.config import EvolveServerConfig
from .engines.agent import AgentEvolveServer
from .engines.workflow import EvolveServer

logger = logging.getLogger("evolve_server")

_DEEPSEEK_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}


def _build_config_from_args(args: argparse.Namespace) -> EvolveServerConfig:
    """Merge CLI args, environment variables, and optionally skillclaw config."""
    config = EvolveServerConfig.from_env()
    source = "env"

    if args.use_skillclaw_config:
        try:
            from skillclaw.config_store import ConfigStore

            sc_config = ConfigStore().to_skillclaw_config()
            config = EvolveServerConfig.from_skillclaw_config(sc_config)
            source = "skillclaw_config"
        except Exception as e:
            logger.warning("Could not load skillclaw config: %s — falling back to env", e)

    if args.engine:
        config.engine = args.engine

    if args.storage_backend:
        config.storage_backend = args.storage_backend
    if args.storage_endpoint or args.oss_endpoint:
        config.storage_endpoint = args.storage_endpoint or args.oss_endpoint
        config.oss_endpoint = config.storage_endpoint
    if args.storage_bucket or args.oss_bucket:
        config.storage_bucket = args.storage_bucket or args.oss_bucket
        config.oss_bucket = config.storage_bucket
    if args.storage_region:
        config.storage_region = args.storage_region
    if args.local_root:
        config.local_root = args.local_root
        if not config.storage_backend:
            config.storage_backend = "local"
    if not config.storage_backend:
        if args.oss_endpoint or args.oss_bucket:
            config.storage_backend = "oss"
        elif config.storage_bucket or (
            config.storage_endpoint
            and str(getattr(config, "skill_storage_backend", "") or "").strip().lower() != "nacos"
        ):
            config.storage_backend = "s3"
    if args.group_id:
        config.group_id = args.group_id
    if args.model:
        config.llm_model = args.model
    if args.llm_api_type:
        config.llm_api_type = args.llm_api_type
    if args.interval:
        config.interval_seconds = args.interval
    if args.port:
        config.http_port = args.port
    if args.publish_mode:
        config.publish_mode = args.publish_mode
    if args.feedback_bundle:
        config.feedback_bundle_path = args.feedback_bundle
    if args.nacos_publish_mode:
        config.nacos_publish_mode = args.nacos_publish_mode
    if args.use_skill_verifier is not None:
        config.use_skill_verifier = args.use_skill_verifier
    if args.skill_verifier_min_score is not None:
        config.skill_verifier_min_score = args.skill_verifier_min_score
    if args.validation_required_results is not None:
        config.validation_required_results = args.validation_required_results
    if args.validation_required_approvals is not None:
        config.validation_required_approvals = args.validation_required_approvals
    if args.validation_min_mean_score is not None:
        config.validation_min_mean_score = args.validation_min_mean_score
    if args.validation_max_rejections is not None:
        config.validation_max_rejections = args.validation_max_rejections
    if args.openclaw_bin:
        config.openclaw_bin = args.openclaw_bin
    if args.openclaw_home:
        config.openclaw_home = args.openclaw_home
    if args.agent_timeout:
        config.agent_timeout = args.agent_timeout
    if args.workspace_root:
        config.workspace_root = args.workspace_root
    if args.agents_md:
        config.agents_md_path = args.agents_md
    if args.fresh is not None:
        config.fresh = args.fresh
    env_override_names = (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "EVOLVE_MODEL",
        "EVOLVE_LLM_API_TYPE",
        "EVOLVE_STORAGE_BACKEND",
        "EVOLVE_STORAGE_LOCAL_ROOT",
    )
    cli_override_names = (
        "engine",
        "storage_backend",
        "storage_endpoint",
        "storage_bucket",
        "storage_region",
        "local_root",
        "group_id",
        "model",
        "llm_api_type",
        "interval",
        "port",
        "publish_mode",
        "feedback_bundle",
        "nacos_publish_mode",
        "use_skill_verifier",
        "skill_verifier_min_score",
        "validation_required_results",
        "validation_required_approvals",
        "validation_min_mean_score",
        "validation_max_rejections",
        "openclaw_bin",
        "openclaw_home",
        "agent_timeout",
        "workspace_root",
        "agents_md",
        "fresh",
    )
    if args.use_skillclaw_config and any(os.environ.get(name) for name in env_override_names):
        source += "+env_overrides"
    if any(getattr(args, name) is not None for name in cli_override_names):
        source += "+cli_overrides"
    config.config_source = source
    config.__post_init__()
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SkillClaw Evolve Server")
    parser.add_argument(
        "--engine",
        choices=["workflow", "agent"],
        default=None,
        help="Evolution engine: fixed workflow or OpenClaw agent.",
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--mock", action="store_true", help="Use local mock/ directory instead of remote object storage"
    )
    parser.add_argument("--mock-root", type=str, default=None, help="Custom root directory for mock mode")
    parser.add_argument("--port", type=int, default=None, help="HTTP trigger port (enables HTTP server)")
    parser.add_argument("--interval", type=int, default=None, help="Periodic interval in seconds")
    parser.add_argument(
        "--publish-mode",
        choices=["direct", "validated"],
        default=None,
        help="Direct publish to skills/ or stage jobs for client-side validation before publish.",
    )
    parser.add_argument(
        "--feedback-bundle",
        type=str,
        default=None,
        help="Runtime JSON feedback bundle consumed by the evolution engine.",
    )
    parser.add_argument(
        "--nacos-publish-mode",
        choices=["draft", "review", "direct"],
        default=None,
        help="Nacos Skill lifecycle mode: draft only, submit for review, or publish latest directly.",
    )
    skill_verifier_group = parser.add_mutually_exclusive_group()
    skill_verifier_group.add_argument(
        "--skill-verifier",
        dest="use_skill_verifier",
        action="store_true",
        default=None,
        help="Enable optional skill verification before upload (workflow engine only).",
    )
    skill_verifier_group.add_argument(
        "--no-skill-verifier",
        dest="use_skill_verifier",
        action="store_false",
        help="Disable optional skill verification before upload.",
    )
    parser.add_argument(
        "--skill-verifier-min-score",
        type=float,
        default=None,
        help="Minimum verifier score in [0, 1] required before a skill is uploaded.",
    )
    parser.add_argument(
        "--validation-required-results",
        type=int,
        default=None,
        help="Minimum client validation results required before a candidate skill is published.",
    )
    parser.add_argument(
        "--validation-required-approvals",
        type=int,
        default=None,
        help="Minimum accepted client validation results required before publish.",
    )
    parser.add_argument(
        "--validation-min-mean-score",
        type=float,
        default=None,
        help="Minimum mean client validation score in [0, 1] required before publish.",
    )
    parser.add_argument(
        "--validation-max-rejections",
        type=int,
        default=None,
        help="Reject the candidate once this many client validation rejections accumulate.",
    )
    parser.add_argument("--model", type=str, default=None, help="LLM model to use")
    parser.add_argument(
        "--llm-api-type",
        type=str,
        default=None,
        choices=["openai-completions", "anthropic-messages", "openai-responses", "google-generative-ai", "ollama"],
        help="LLM provider API type. Primarily used by --engine agent.",
    )
    parser.add_argument("--group-id", type=str, default=None, help="Shared storage group ID")
    parser.add_argument("--storage-backend", type=str, default=None, help="Storage backend: local, s3, or oss")
    parser.add_argument("--storage-endpoint", type=str, default=None)
    parser.add_argument("--storage-bucket", type=str, default=None)
    parser.add_argument("--storage-region", type=str, default=None)
    parser.add_argument("--oss-endpoint", type=str, default=None)
    parser.add_argument("--oss-bucket", type=str, default=None)
    parser.add_argument(
        "--local-root",
        type=str,
        default=None,
        help="Use a local directory as the evolve backend root",
    )
    parser.add_argument(
        "--use-skillclaw-config",
        action="store_true",
        help="Load shared storage and LLM settings from skillclaw's config store",
    )
    parser.add_argument("--openclaw-bin", type=str, default=None, help="Path to openclaw executable for --engine agent")
    parser.add_argument("--openclaw-home", type=str, default=None, help="OPENCLAW_HOME directory for --engine agent")
    fresh_group = parser.add_mutually_exclusive_group()
    fresh_group.add_argument(
        "--fresh",
        dest="fresh",
        action="store_true",
        default=None,
        help="Wipe agent state each cycle (agent engine only)",
    )
    fresh_group.add_argument(
        "--no-fresh", dest="fresh", action="store_false", help="Preserve agent state across cycles (agent engine only)"
    )
    parser.add_argument("--agent-timeout", type=int, default=None, help="Agent execution timeout in seconds")
    parser.add_argument(
        "--workspace-root", type=str, default=None, help="Workspace directory for agent file operations"
    )
    parser.add_argument("--agents-md", type=str, default=None, help="Custom EVOLVE_AGENTS.md path for agent engine")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def _build_server(
    config: EvolveServerConfig,
    *,
    mock: bool = False,
    mock_root: str | None = None,
):
    if config.engine == "agent":
        return AgentEvolveServer(config, mock=mock, mock_root=mock_root)
    return EvolveServer(config, mock=mock, mock_root=mock_root)


def _validate_llm_runtime_config(config: EvolveServerConfig) -> None:
    base_url = str(config.llm_base_url or "").strip().lower()
    model = str(config.llm_model or "").strip()
    if "api.deepseek.com" in base_url and model not in _DEEPSEEK_MODELS:
        raise SystemExit(
            "DeepSeek base URL requires --model deepseek-v4-pro or deepseek-v4-flash. "
            "Use --use-skillclaw-config or pass --model explicitly."
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    config = _build_config_from_args(args)
    _validate_llm_runtime_config(config)
    logger.info(
        "[EvolveServer] resolved config source=%s llm base=%s model=%s publish_mode=%s storage=%s",
        config.config_source,
        config.llm_base_url,
        config.llm_model,
        config.publish_mode,
        config.storage_backend or "(unset)",
    )

    if not args.mock:
        backend = (config.storage_backend or "").strip().lower()
        if backend == "local":
            if not config.local_root:
                logger.error("Local storage backend requires --local-root or EVOLVE_STORAGE_LOCAL_ROOT.")
                raise SystemExit(1)
        elif backend == "oss":
            if not config.storage_endpoint or not config.storage_bucket:
                logger.error(
                    "OSS backend requires endpoint and bucket. "
                    "Set EVOLVE_STORAGE_ENDPOINT / EVOLVE_STORAGE_BUCKET, use legacy EVOLVE_OSS_* vars, "
                    "or use --use-skillclaw-config."
                )
                raise SystemExit(1)
        elif not backend:
            if str(getattr(config, "skill_storage_backend", "") or "").strip().lower() == "nacos":
                logger.error(
                    "sharing.skill_backend=nacos stores skill assets only. Configure session storage with "
                    "sharing.backend, sharing.session_backend, sharing.local_root, EVOLVE_STORAGE_*, or use --mock."
                )
                raise SystemExit(1)
            logger.error(
                "Storage backend is not configured. Set EVOLVE_STORAGE_BACKEND, use --use-skillclaw-config, "
                "use --local-root for local mode, or use --mock."
            )
            raise SystemExit(1)
        else:
            if not config.storage_bucket:
                logger.error(
                    "Storage bucket is required for remote backends. "
                    "Set EVOLVE_STORAGE_BUCKET, use legacy EVOLVE_OSS_BUCKET, "
                    "use --use-skillclaw-config, use --local-root for local mode, or use --mock."
                )
                raise SystemExit(1)

    server = _build_server(config, mock=args.mock, mock_root=args.mock_root)

    if args.once or args.mock:
        summary = asyncio.run(server.run_once())
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    if args.port is not None:
        import uvicorn

        app = server.create_http_app()

        async def _run_with_http():
            uv_config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=config.http_port,
                log_level="info",
            )
            uv_server = uvicorn.Server(uv_config)
            await asyncio.gather(server.run_periodic(), uv_server.serve())

        asyncio.run(_run_with_http())
    else:
        asyncio.run(server.run_periodic())


if __name__ == "__main__":
    main()
