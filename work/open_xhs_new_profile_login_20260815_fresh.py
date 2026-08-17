from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = Path.home() / ".xiaohongshu" / "browser-data-insforge-20260815-fresh"


sys.argv = [
    str(ROOT / "work" / "open_xhs_new_profile_login.py"),
    "--profile-dir",
    str(PROFILE_DIR),
    "--seconds",
    "900",
    "--url",
    "https://www.xiaohongshu.com/explore",
]

runpy.run_path(str(ROOT / "work" / "open_xhs_new_profile_login.py"), run_name="__main__")
