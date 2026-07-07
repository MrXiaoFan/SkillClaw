#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
exec bash ../experiment_cases/pocs/libxml2-2.9.4-cve-2017-8872/confirm_logic_window.sh
