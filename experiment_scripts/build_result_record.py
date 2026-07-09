import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_scripts.postprocess.build_result_record import *  # noqa: F401,F403
from experiment_scripts.postprocess.build_result_record import (
    _load_optional_json,
    _select_injection,
    _select_injection_history,
    _select_validation,
)


if __name__ == "__main__":
    raise SystemExit(main())
