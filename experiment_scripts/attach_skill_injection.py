import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_scripts.postprocess.attach_skill_injection import *  # noqa: F401,F403
from experiment_scripts.postprocess.attach_skill_injection import _load_json


if __name__ == "__main__":
    raise SystemExit(main())
