#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

INPUT_PATH="${ROOT}/artifacts/libarchive-cve-2025-60753-input.txt"
RULE="$(tr -d '\r\n' < "${ROOT}/artifacts/libarchive-cve-2025-60753-rule.txt")"
OUT_TAR="${ROOT}/artifacts/libarchive-cve-2025-60753-out.tar"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

cp "${INPUT_PATH}" "${WORKDIR}/f"
rm -f "${OUT_TAR}"

set +e
timeout 5s ./bsdtar -cf "${OUT_TAR}" -s "${RULE}" "${WORKDIR}/f" >/dev/null 2>&1
RC=$?
set -e

OUT_SIZE=0
if [[ -f "${OUT_TAR}" ]]; then
  OUT_SIZE="$(wc -c < "${OUT_TAR}")"
fi

if [[ "${RC}" -eq 124 ]]; then
  echo "TIMEOUT_CONFIRM_OK libarchive-empty-global-substitution"
  echo "expected_rc=124"
  echo "out_tar_size=${OUT_SIZE}"
  exit 0
fi

echo "unexpected_rc=${RC}" >&2
echo "out_tar_size=${OUT_SIZE}" >&2
exit 1
