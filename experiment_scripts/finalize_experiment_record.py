import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_scripts.postprocess.finalize_experiment_record import *  # noqa: F401,F403


if __name__ == "__main__":
    raise SystemExit(main())
