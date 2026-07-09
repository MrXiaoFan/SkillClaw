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
    (root / ".libs" / "xmllint_asan").write_text("synthetic xmllint asan placeholder\n", encoding="utf-8")
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "artifacts" / "libxml2-cve-2017-8872-input.html").write_text(
        "<!DOCTYPE html><!\n",
        encoding="utf-8",
    )
    (root / "artifacts" / "run_libxml2_logic_confirm.sh").write_text(
        "#!/bin/sh\n"
        "echo 'LOGIC_CONFIRM_OK libxml2-state-machine-window'\n"
        "exit 0\n",
        encoding="utf-8",
    )
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


def _write_tcpdump_isakmp_fixture(root: Path) -> None:
    (root / "tcpdump").write_text("synthetic tcpdump placeholder\n", encoding="utf-8")
    (root / "print-isakmp.c").write_text(
        """
#define IPSECDOI_NTYPE_REPLAY_STATUS 24577

int ikev1_n_print(const unsigned char *cp, unsigned int spi_size, const unsigned char *ep) {
    if (cp < ep) {
        return (int)spi_size + (int)EXTRACT_32BITS(cp);
    }
    return 0;
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    pcap = root / "artifacts" / "poc-cve-2018-14469.pcap"
    pcap.write_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 96)
    (root / "artifacts" / "run_tcpdump_isakmp_poc.sh").write_text(
        "#!/bin/sh\n"
        "echo 'isakmp 1.0: (n: doi=ipsec proto=isakmp type=REPLAY-STATUS spi=04 orig=(replay detection enabled)) (len mismatch: isakmp 41/ip 45)'\n"
        "exit 0\n",
        encoding="utf-8",
    )


def _write_libarchive_fixture(root: Path) -> None:
    (root / "tar").mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "bsdtar").write_text("synthetic bsdtar placeholder\n", encoding="utf-8")
    (root / "tar" / "subst.c").write_text(
        """
int apply_substitution(void) {
    /* rule->global */
    int regexec_status = 0;
    int rm_eo = 0;
    if (/* rule->global */ 1 && !regexec_status) {
        /* matches[0].rm_eo */
        rm_eo = 0;
        /* name += matches[0].rm_eo */
    }
    /* regexec */
    return rm_eo;
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "artifacts" / "libarchive-cve-2025-60753-input.txt").write_text("f\n", encoding="utf-8")
    (root / "artifacts" / "libarchive-cve-2025-60753-rule.txt").write_text(",,A,g\n", encoding="utf-8")
    (root / "artifacts" / "run_libarchive_poc.sh").write_text(
        "#!/bin/sh\n"
        "echo 'TIMEOUT_CONFIRM_OK libarchive-empty-global-substitution'\n"
        "echo 'expected_rc=124'\n"
        "echo 'out_tar_size=0'\n"
        "exit 0\n",
        encoding="utf-8",
    )


def _write_exiv2_fixture(root: Path) -> None:
    (root / "bin").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "bin" / "exiv2").write_text("synthetic exiv2 placeholder\n", encoding="utf-8")
    (root / "src" / "types.cpp").write_text(
        """
enum ByteOrder { littleEndian, bigEndian, invalidByteOrder };

static unsigned long getULong(const unsigned char* data, long offset, long bounds) {
    /* TIFF */
    if (offset >= bounds) {
        return 0;
    }
    return (unsigned long)data[offset];
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "src" / "jp2image.cpp").write_text(
        """
struct DataBuf {
    explicit DataBuf(int size) : size_(size) {}
    int size_;
};

static void readMetadata(void) {
    DataBuf rawData(5);
    (void)rawData.size_;
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    poc_bytes = (
        b"II" + b"\x2a\x00" + b"\x08\x00\x00\x00" + b"\x00\x00" + (b"\x00" * 32)
    )
    (root / "artifacts" / "poc-cve-2017-17725.jp2").write_bytes(poc_bytes)
    (root / "artifacts" / "poc-cve-2017-17725.tiff").write_bytes(poc_bytes)
    (root / "artifacts" / "run_exiv2_poc.sh").write_text(
        "#!/bin/sh\n"
        "if [ \"${1:-}\" = \"--smoke-only\" ]; then\n"
        "  echo 'RUN_EXIV2_POC target=./bin/exiv2 input=artifacts/poc-cve-2017-17725.jp2 smoke=1' 1>&2\n"
        "  echo 'WRAPPER_SMOKE_OK exiv2-artifact-wrapper' 1>&2\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"${1:-}\" = \"--probe-only\" ]; then\n"
        "  echo 'RUN_EXIV2_POC target=./bin/exiv2 input=artifacts/poc-cve-2017-17725.jp2 probe=1' 1>&2\n"
        "  echo 'synthetic exiv2 probe output'\n"
        "  echo 'WRAPPER_PROBE_OK exiv2-artifact-wrapper' 1>&2\n"
        "  echo 'TARGET_EXECUTION_RC=1' 1>&2\n"
        "  exit 0\n"
        "fi\n"
        "echo 'RUN_EXIV2_POC target=./bin/exiv2 input=artifacts/poc-cve-2017-17725.jp2 behavior=1' 1>&2\n"
        "echo 'Jp2Image::readMetadata DataBuf(5)' 1>&2\n"
        "echo 'AddressSanitizer: heap-buffer-overflow in getULong (types.cpp)' 1>&2\n"
        "echo 'EXIV2_JP2_ICC_PATH_OK jp2-readmetadata-getulong' 1>&2\n"
        "echo 'EXIV2_ASAN_OOB_OK heap-buffer-overflow' 1>&2\n"
        "echo 'TARGET_EXECUTION_RC=134' 1>&2\n"
        "exit 134\n",
        encoding="utf-8",
    )


def _prepare_fixture(case: dict[str, Any], root: Path) -> None:
    case_id = str(case.get("case_id", ""))
    if "libxml2" in case_id:
        _write_libxml2_fixture(root)
    elif "tcpdump-4.9.1-cve-2018-14469" in case_id:
        _write_tcpdump_isakmp_fixture(root)
    elif "libarchive" in case_id:
        _write_libarchive_fixture(root)
    elif "exiv2" in case_id:
        _write_exiv2_fixture(root)
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
