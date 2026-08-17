from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "work" / "xhs_incremental_verify_required_state_20260813_20260815_rerun.json"
PROFILE_DIR = Path.home() / ".xiaohongshu" / "browser-data-insforge-20260815-fresh"

data = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
url = data.get("url") or "https://www.xiaohongshu.com/explore"

sys.argv = [
    str(ROOT / "work" / "open_xhs_visible_url_proxy.py"),
    "--url",
    url,
    "--seconds",
    "900",
    "--profile-dir",
    str(PROFILE_DIR),
]

runpy.run_path(str(ROOT / "work" / "open_xhs_visible_url_proxy.py"), run_name="__main__")
