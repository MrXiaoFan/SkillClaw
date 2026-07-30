#!/usr/bin/env python3
"""查看 OSS 存储目录下同一 client_session_id 对应的所有 segment 文件。

遍历 sessions/ 目录下的所有 JSON 文件，按 client_session_id 分组，
列出每个 session 的所有 segment（含状态、时间、turn 数）。

用法：
    # 默认本地存储 .local-share
    python scripts/ops/list_session_segments.py

    # 指定存储根目录
    python scripts/ops/list_session_segments.py --root /path/to/.local-share

    # 指定 group-id (prefix)
    python scripts/ops/list_session_segments.py --prefix default/

    # 只看指定 client_session_id
    python scripts/ops/list_session_segments.py --session abc-123

    # 只看 closed 的 segment
    python scripts/ops/list_session_segments.py --status closed
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def _load_json(file: Path) -> dict | None:
    try:
        return json.loads(file.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        print(f"  [warn] 解析失败 {file.name}: {e}", file=sys.stderr)
        return None


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "?"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M:%S")
    except Exception:
        return ts[:19]


def main() -> None:
    parser = argparse.ArgumentParser(description="List session segments from OSS/local storage")
    parser.add_argument(
        "--root",
        default=None,
        help="Storage root (default: auto-detect .local-share or cwd)",
    )
    parser.add_argument(
        "--prefix",
        default="default/",
        help="Group prefix (default: default/)",
    )
    parser.add_argument("--session", default=None, help="Filter by client_session_id")
    parser.add_argument("--status", default=None, help="Filter by segment_status (active/closed)")
    args = parser.parse_args()

    # 确定存储根目录
    root = Path(args.root) if args.root else None
    if not root:
        candidates = [
            Path.cwd() / ".local-share",
            Path.cwd().parent / ".local-share",
            Path.home() / ".local-share",
        ]
        for c in candidates:
            if c.is_dir():
                root = c
                break
    if not root:
        print("Error: 找不到 .local-share 目录，请用 --root 指定", file=sys.stderr)
        sys.exit(1)

    sessions_dir = root / args.prefix.strip("/") / "sessions"
    if not sessions_dir.is_dir():
        print(f"Error: sessions 目录不存在: {sessions_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(sessions_dir.glob("*.json"))
    if not files:
        print(f"在 {sessions_dir} 下未找到任何 segment 文件")
        return

    # 按 client_session_id 分组
    groups: dict[str, list[tuple[Path, dict]]] = {}
    for f in files:
        data = _load_json(f)
        if data is None:
            continue
        cid = str(data.get("client_session_id") or data.get("session_id") or "").strip()
        if cid:
            groups.setdefault(cid, []).append((f, data))

    if not groups:
        print("所有 JSON 文件均无法解析 client_session_id")
        return

    # 过滤
    if args.session:
        groups = {k: v for k, v in groups.items() if args.session in k}
    if not groups:
        print(f"未找到匹配 '{args.session}' 的 session")
        return

    # 打印
    total = sum(len(items) for items in groups.values())
    print(f"\n存储目录: {sessions_dir}")
    print(f"Segments: {total} 个，Sessions: {len(groups)} 个\n")

    for cid in sorted(groups):
        items = groups[cid]
        print(f"📦 client_session_id: {cid}  ({len(items)} 个 segment)")
        print(
            f"    {'文件名':<40} {'Segment ID':<36}"
            f" {'状态':<8} {'开始时间':<16} {'关闭时间':<16} {'Turns'}"
        )
        print(f"    {'-'*40} {'-'*36} {'-'*8} {'-'*16} {'-'*16} {'-'*5}")

        for f, data in sorted(items, key=lambda x: x[1].get("timestamp", "")):
            seg_id = str(data.get("session_segment_id") or "?").strip()
            status = str(data.get("segment_status") or "?").strip()
            ts = _fmt_ts(data.get("timestamp"))
            closed_at = _fmt_ts(data.get("segment_closed_at"))
            turns = data.get("num_turns", data.get("turn_count", "?"))
            # 过滤
            if args.status and status != args.status:
                continue

            # 用文件名而不是 seg_id 做显示（因为文件名就是 seg_id.json）
            print(
                f"    {f.name:<40} {seg_id:<36}"
                f" {status:<8} {ts:<16} {closed_at:<16} {turns}"
            )

        # 匹配该 client_session_id 的 run_feedback
        feedback_dir = root / args.prefix.strip("/") / "run_feedback"
        if feedback_dir.is_dir():
            feedback_segments = [d for d in feedback_dir.iterdir() if d.is_dir()]
            has_feedback = False
            for fb_seg_dir in sorted(feedback_segments):
                # 检查这个 feedback segment 下是否有文件引用了这个 client_session_id
                for fb_file in sorted(fb_seg_dir.glob("*.json")):
                    fb_data = _load_json(fb_file)
                    if fb_data and str(fb_data.get("client_session_id") or "") == cid:
                        if not has_feedback:
                            print(f"\n    📎 关联的 run_feedback:")
                            has_feedback = True
                        seg = fb_data.get("session_segment_id", fb_seg_dir.name)
                        print(
                            f"      {fb_file.parent.name}/{fb_file.name}  "
                            f"segment={seg}  validation_status={fb_data.get('validation_status', '?')}"
                        )
                        break
        print()

    print(f"总计: {total} 个 segment\n")


if __name__ == "__main__":
    main()
