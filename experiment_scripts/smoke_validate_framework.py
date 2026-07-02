#!/usr/bin/env python3
"""Smoke-test the experiment validation framework without an LLM or VM target.

The real benchmark cases point at remote VM source trees.  This script creates
tiny synthetic source trees that contain the ground-truth symbols needed by the
case validators, then runs the case-level validation pipeline.  It is intended
as the first command a collaborator runs after cloning the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from experiment_validation.runner import run_case_validators
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_validation.runner import run_case_validators


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_case(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _write_libxml2_fixture(root: Path) -> None:
    (root / ".libs").mkdir(parents=True, exist_ok=True)
    (root / ".libs" / "xmllint").write_text("synthetic xmllint placeholder\n", encoding="utf-8")
    (root / "HTMLparser.c").write_text(
        """
typedef struct { const unsigned char *cur; } input_t;
static input_t *in;

static void htmlParseTryOrFinish(void) {
    int avail = 2;
    if (avail < 2) {
        return;
    }
    (void) in->cur[2];
    (void) in->cur[3];
}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_tcpdump_fixture(root: Path) -> None:
    (root / "tcpdump").write_text("synthetic tcpdump placeholder\n", encoding="utf-8")
    (root / "print-frag6.c").write_text(
        """
struct ip6_frag { int ip6f_offlg; int ip6f_ident; };

int frag6_print(const struct ip6_frag *dp) {
    ND_TCHECK(dp->ip6f_offlg);
    return dp->ip6f_ident;
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    pcap = root / "artifacts" / "poc-cve-2017-13031.pcap"
    pcap.write_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 92)
    (root / "artifacts" / "run_tcpdump_frag6_poc.sh").write_text(
        "#!/bin/sh\n"
        "echo 'IP6 (hlim 64, next-header Fragment (44) payload length: 8) 2001:db8::1 > 2001:db8::2: [|frag]'\n"
        "exit 0\n",
        encoding="utf-8",
    )


def _prepare_fixture(case: dict[str, Any], root: Path) -> None:
    case_id = str(case.get("case_id", ""))
    if "libxml2" in case_id:
        _write_libxml2_fixture(root)
    elif "tcpdump" in case_id:
        _write_tcpdump_fixture(root)
    elif "giflib" in case_id:
        (root / "util").mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(parents=True, exist_ok=True)
        (root / "util" / "gif2rgb.c").write_text(
            "\n".join(
                [
                    "void DumpScreen2RGB(void) {",
                    "  /* GifFile->SBackGroundColor */",
                    "  /* ScreenBuffer[0][i] */",
                    "  /* ColorMap->Colors[GifRow[j]] */",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "artifacts" / "poc-cve-2016-3977.gif").write_bytes(b"GIF89a" + b"\x00" * 14)
        (root / "artifacts" / "run_giflib_poc.sh").write_text(
            "#!/bin/sh\n"
            "echo 'AddressSanitizer: heap-buffer-overflow in DumpScreen2RGB' 1>&2\n"
            "exit 134\n",
            encoding="utf-8",
        )
    else:
        truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
        files = [str(item) for item in truth.get("files", []) if str(item).strip()]
        evidence = [str(item) for item in truth.get("required_evidence", []) if str(item).strip()]
        functions = [str(item) for item in truth.get("functions", []) if str(item).strip()]
        for rel_file in files:
            (root / rel_file).parent.mkdir(parents=True, exist_ok=True)
            (root / rel_file).write_text("\n".join(functions + evidence) + "\n", encoding="utf-8")


def _case_paths(cases_dir: Path) -> list[Path]:
    return sorted(path for path in cases_dir.glob("*.json") if path.name != "schema.json")


def smoke_cases(cases_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case_path in _case_paths(cases_dir):
        case = _load_case(case_path)
        with tempfile.TemporaryDirectory(prefix=f"skillclaw-smoke-{case_path.stem}-") as tmp:
            root = Path(tmp)
            _prepare_fixture(case, root)
            result = run_case_validators(
                case,
                root,
                case_path=case_path,
                agent_output_path=None,
                skip_commands=True,
            )
            results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", type=Path, default=REPO_ROOT / "experiment_cases")
    parser.add_argument("--json", action="store_true", help="Print full JSON results.")
    args = parser.parse_args(argv)

    results = smoke_cases(args.cases_dir)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"{item.get('case_id')}: {item.get('status')}")

    failed = [item for item in results if item.get("status") == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
