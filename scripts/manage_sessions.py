#!/usr/bin/env python3
"""List or delete SkillClaw proxy sessions via the REST API.

Usage:
    # List all active sessions
    python scripts/manage_sessions.py list

    # Delete a specific session
    python scripts/manage_sessions.py delete <session_id>

    # Delete all sessions (with confirmation)
    python scripts/manage_sessions.py delete-all

    # Custom host/port/api-key
    python scripts/manage_sessions.py list --host 10.0.0.1 --port 30001 --api-key sk-xxx
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Try to load config so CLI defaults come from ~/.skillclaw/config.yaml.
try:
    from skillclaw.config_store import ConfigStore  # type: ignore[import-untyped]

    _CONFIG = ConfigStore().to_skillclaw_config()
except Exception:
    _CONFIG = None


def _config_host() -> str:
    return _CONFIG.proxy_host if _CONFIG else "127.0.0.1"


def _config_port() -> int:
    return _CONFIG.proxy_port if _CONFIG else 30000


def _config_api_key() -> str:
    return _CONFIG.proxy_api_key if _CONFIG else ""


_API_KEY_ENV_VAR = "SKILLCLAW_PROXY_API_KEY"


def _build_url(host: str, port: int, path: str) -> str:
    return f"http://{host}:{port}{path}"


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def list_sessions(host: str, port: int, api_key: str | None) -> None:
    url = _build_url(host, port, "/v1/sessions")
    req = Request(url, headers=_build_headers(api_key), method="GET")

    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: cannot connect to {url} — {e.reason}", file=sys.stderr)
        sys.exit(1)

    sessions = data.get("sessions", [])
    if not sessions:
        print("No active sessions.")
        return

    print(f"{'Session ID':<48} {'Idle (s)':<10} {'Turns':<8} {'Closing':<8}")
    print("-" * 74)
    for s in sessions:
        print(
            f"{s['session_id']:<48} "
            f"{s.get('idle_seconds', '?'):<10} "
            f"{s.get('turn_count', 0):<8} "
            f"{'yes' if s.get('is_closing') else 'no':<8}"
        )
    print(f"\nTotal: {len(sessions)} session(s)")


def delete_session(session_id: str, host: str, port: int, api_key: str | None) -> None:
    url = _build_url(host, port, f"/v1/sessions/{session_id}")
    req = Request(url, headers=_build_headers(api_key), method="DELETE")

    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode()
        detail = json.loads(body).get("detail", e.reason) if body else e.reason
        print(f"Error: {e.code} — {detail}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: cannot connect to {url} — {e.reason}", file=sys.stderr)
        sys.exit(1)

    print(f"Deleted session: {data.get('session_id')}")


def delete_all_sessions(host: str, port: int, api_key: str | None, force: bool = False) -> None:
    # Fetch current list
    sessions = _fetch_sessions(host, port, api_key)
    if not sessions:
        print("No active sessions to delete.")
        return

    if not force:
        print(f"This will delete {len(sessions)} active session(s):")
        for s in sessions:
            print(f"  {s['session_id']}")
        confirm = input("Are you sure? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    failed = 0
    for s in sessions:
        try:
            delete_session(s["session_id"], host, port, api_key)
        except SystemExit:
            failed += 1

    if failed:
        print(f"\nDone ({len(sessions) - failed} deleted, {failed} failed)")
    else:
        print(f"\nDeleted all {len(sessions)} session(s)")


def _fetch_sessions(host: str, port: int, api_key: str | None) -> list[dict]:
    url = _build_url(host, port, "/v1/sessions")
    req = Request(url, headers=_build_headers(api_key), method="GET")
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: cannot connect to {url} — {e.reason}", file=sys.stderr)
        sys.exit(1)
    return data.get("sessions", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage SkillClaw proxy sessions")
    parser.add_argument(
        "--host",
        default=os.environ.get("SKILLCLAW_PROXY_HOST") or _config_host(),
        help="Proxy host (env: SKILLCLAW_PROXY_HOST, "
        f"default from config: {_config_host()})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SKILLCLAW_PROXY_PORT") or _config_port()),
        help="Proxy port (env: SKILLCLAW_PROXY_PORT, "
        f"default from config: {_config_port()})",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get(_API_KEY_ENV_VAR) or _config_api_key(),
        help=f"API key for auth (env: {_API_KEY_ENV_VAR}, "
        f"default from config: {_config_api_key() or '(none)'})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all active sessions")

    # delete <session_id>
    del_parser = subparsers.add_parser("delete", help="Delete a specific session")
    del_parser.add_argument("session_id", help="Session ID to delete")

    # delete-all
    del_all_parser = subparsers.add_parser("delete-all", help="Delete all active sessions")
    del_all_parser.add_argument(
        "-f", "--force", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    api_key = args.api_key or None  # treat empty string as None

    if args.command == "list":
        list_sessions(args.host, args.port, api_key)
    elif args.command == "delete":
        delete_session(args.session_id, args.host, args.port, api_key)
    elif args.command == "delete-all":
        delete_all_sessions(args.host, args.port, api_key, args.force)


if __name__ == "__main__":
    main()
