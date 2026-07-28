#!/usr/bin/env python3
"""Connect to a remote experiment VM, run commands, transfer files, and log each action."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import paramiko
except ImportError:  # pragma: no cover - handled at runtime for optional dependency.
    paramiko = None  # type: ignore[assignment]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_key_path() -> Path | None:
    candidate = Path.home() / ".ssh" / "skillclaw_vm"
    return candidate if candidate.is_file() else None


def _default_log_path() -> Path:
    return Path("runtime") / "logs" / "remote_vm_commands.log"


@dataclass(slots=True)
class RemoteExperimentVmConfig:
    host: str
    username: str
    port: int = 22
    key_path: Path | None = None
    password: str | None = None
    connect_timeout: float = 10.0

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RemoteExperimentVmConfig":
        key_path = Path(args.key_path).expanduser() if getattr(args, "key_path", None) else _default_key_path()
        password = getattr(args, "password", None) or os.environ.get("SKILLCLAW_REMOTE_PASSWORD")
        port = getattr(args, "port", None)
        if port is None:
            port = int(os.environ.get("SKILLCLAW_REMOTE_PORT", "22"))
        connect_timeout = getattr(args, "connect_timeout", None)
        if connect_timeout is None:
            connect_timeout = float(os.environ.get("SKILLCLAW_REMOTE_CONNECT_TIMEOUT", "10"))
        return cls(
            host=args.host or os.environ.get("SKILLCLAW_REMOTE_HOST", ""),
            username=args.user or os.environ.get("SKILLCLAW_REMOTE_USER", ""),
            port=int(port),
            key_path=key_path,
            password=password,
            connect_timeout=float(connect_timeout),
        )

    def auth_mode(self) -> str:
        if self.key_path:
            return "ssh_key"
        if self.password:
            return "password"
        return "unknown"


class RemoteExperimentVmClient:
    def __init__(self, config: RemoteExperimentVmConfig) -> None:
        if paramiko is None:  # pragma: no cover - dependency guard.
            raise RuntimeError("paramiko is required for evaluation.remote.experiment_vm")
        if not config.host.strip():
            raise ValueError("remote host is required")
        if not config.username.strip():
            raise ValueError("remote username is required")
        self.config = config
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        if self._client is not None:
            return
        base_kwargs: dict[str, Any] = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.connect_timeout,
            "banner_timeout": self.config.connect_timeout,
            "auth_timeout": self.config.connect_timeout,
        }
        attempts: list[dict[str, Any]] = []
        if self.config.key_path:
            attempts.append({**base_kwargs, "key_filename": str(self.config.key_path)})
        if self.config.password:
            attempts.append({**base_kwargs, "password": self.config.password})
        if not attempts:
            attempts.append(base_kwargs)

        last_error: Exception | None = None
        for connect_kwargs in attempts:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(**connect_kwargs)
                self._client = client
                return
            except Exception as exc:  # pragma: no cover - network/auth dependent.
                last_error = exc
                client.close()
        assert last_error is not None
        raise last_error

    def close(self) -> None:
        if self._client is None:
            return
        self._client.close()
        self._client = None

    def __enter__(self) -> "RemoteExperimentVmClient":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def run(
        self,
        command: str,
        *,
        cwd: str | None = None,
        timeout: float | None = None,
        log_path: Path | None = None,
    ) -> dict[str, Any]:
        self.connect()
        assert self._client is not None
        remote_command = command
        if cwd:
            remote_command = f"cd {shlex.quote(cwd)} && {command}"
        started_at = _utc_now()
        stdin, stdout, stderr = self._client.exec_command(remote_command, timeout=timeout)
        stdin.close()
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        exit_status = int(stdout.channel.recv_exit_status())
        result = {
            "action": "run",
            "host": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "auth_mode": self.config.auth_mode(),
            "cwd": cwd,
            "command": command,
            "remote_command": remote_command,
            "started_at": started_at,
            "ended_at": _utc_now(),
            "exit_status": exit_status,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }
        self._append_log(log_path or _default_log_path(), result)
        return result

    def upload(self, local_path: Path, remote_path: str, *, log_path: Path | None = None) -> dict[str, Any]:
        self.connect()
        assert self._client is not None
        started_at = _utc_now()
        with self._client.open_sftp() as sftp:
            sftp.put(str(local_path), remote_path)
        result = {
            "action": "upload",
            "host": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "auth_mode": self.config.auth_mode(),
            "local_path": str(local_path),
            "remote_path": remote_path,
            "started_at": started_at,
            "ended_at": _utc_now(),
            "size": local_path.stat().st_size if local_path.exists() else None,
        }
        self._append_log(log_path or _default_log_path(), result)
        return result

    def download(self, remote_path: str, local_path: Path, *, log_path: Path | None = None) -> dict[str, Any]:
        self.connect()
        assert self._client is not None
        local_path.parent.mkdir(parents=True, exist_ok=True)
        started_at = _utc_now()
        with self._client.open_sftp() as sftp:
            sftp.get(remote_path, str(local_path))
        result = {
            "action": "download",
            "host": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "auth_mode": self.config.auth_mode(),
            "remote_path": remote_path,
            "local_path": str(local_path),
            "started_at": started_at,
            "ended_at": _utc_now(),
            "size": local_path.stat().st_size if local_path.exists() else None,
        }
        self._append_log(log_path or _default_log_path(), result)
        return result

    @staticmethod
    def _append_log(path: Path, result: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"=== {_utc_now()} ===",
            f"action: {result.get('action')}",
            f"host: {result.get('username')}@{result.get('host')}:{result.get('port')}",
            f"auth_mode: {result.get('auth_mode')}",
        ]
        if result.get("cwd"):
            lines.append(f"cwd: {result['cwd']}")
        if result.get("command"):
            lines.append(f"command: {result['command']}")
        if result.get("remote_command"):
            lines.append(f"remote_command: {result['remote_command']}")
        if result.get("local_path"):
            lines.append(f"local_path: {result['local_path']}")
        if result.get("remote_path"):
            lines.append(f"remote_path: {result['remote_path']}")
        if "exit_status" in result:
            lines.append(f"exit_status: {result['exit_status']}")
        if result.get("size") is not None:
            lines.append(f"size: {result['size']}")
        lines.append(f"started_at: {result.get('started_at')}")
        lines.append(f"ended_at: {result.get('ended_at')}")
        stdout_text = str(result.get("stdout") or "")
        stderr_text = str(result.get("stderr") or "")
        if stdout_text:
            lines.extend(["[stdout]", stdout_text.rstrip("\n")])
        if stderr_text:
            lines.extend(["[stderr]", stderr_text.rstrip("\n")])
        lines.append("")
        path.write_text(
            path.read_text(encoding="utf-8", errors="replace") + "\n".join(lines),
            encoding="utf-8",
        ) if path.exists() else path.write_text("\n".join(lines), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="Remote VM host. Default: $env:SKILLCLAW_REMOTE_HOST")
    parser.add_argument("--user", help="Remote VM username. Default: $env:SKILLCLAW_REMOTE_USER")
    parser.add_argument("--port", type=int, default=None, help="SSH port.")
    parser.add_argument("--key-path", help="Private key path. Default: ~/.ssh/skillclaw_vm if present.")
    parser.add_argument("--password", help="Password. Default: $env:SKILLCLAW_REMOTE_PASSWORD")
    parser.add_argument("--connect-timeout", type=float, default=None)
    parser.add_argument(
        "--log-path",
        type=Path,
        default=_default_log_path(),
        help="Plain-text log file for commands and outputs.",
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("check", help="Verify remote connectivity.")

    run_parser = subparsers.add_parser("run", help="Run one remote command.")
    run_parser.add_argument("command", help="Shell command to run on the remote VM.")
    run_parser.add_argument("--cwd", help="Remote working directory before the command runs.")
    run_parser.add_argument("--timeout", type=float, default=None)

    upload_parser = subparsers.add_parser("upload", help="Upload one file.")
    upload_parser.add_argument("local_path", type=Path)
    upload_parser.add_argument("remote_path")

    download_parser = subparsers.add_parser("download", help="Download one file.")
    download_parser.add_argument("remote_path")
    download_parser.add_argument("local_path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = RemoteExperimentVmConfig.from_args(args)

    with RemoteExperimentVmClient(config) as client:
        if args.action == "check":
            result = client.run("hostname && whoami && pwd", log_path=args.log_path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("exit_status") == 0 else 1
        if args.action == "run":
            result = client.run(args.command, cwd=args.cwd, timeout=args.timeout, log_path=args.log_path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result.get("exit_status") or 0)
        if args.action == "upload":
            result = client.upload(args.local_path, args.remote_path, log_path=args.log_path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.action == "download":
            result = client.download(args.remote_path, args.local_path, log_path=args.log_path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    raise AssertionError(f"unsupported action: {args.action}")


if __name__ == "__main__":
    raise SystemExit(main())
