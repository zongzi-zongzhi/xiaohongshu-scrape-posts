from __future__ import annotations

import os
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ["XHS_BROWSER_PROFILE_DIR"] = str(Path.home() / ".xiaohongshu" / "browser-data-insforge-20260815-fresh")

runpy.run_path(
    str(ROOT / "work" / "crawl_xhs_incremental_20260813_20260815_rerun_merge_master_pointer.py"),
    run_name="__main__",
)
