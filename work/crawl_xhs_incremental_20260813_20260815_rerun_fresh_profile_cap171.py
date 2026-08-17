from __future__ import annotations

import os
from pathlib import Path


os.environ["XHS_BROWSER_PROFILE_DIR"] = str(Path.home() / ".xiaohongshu" / "browser-data-insforge-20260815-fresh")

import crawl_xhs_incremental_20260813_20260815_rerun_merge_master_pointer as rerun


job = rerun.job
_original_effective_keywords = job.effective_keywords


def _capped_effective_keywords(max_keywords: int = 0) -> list[str]:
    queue = _original_effective_keywords(0)[:171]
    if max_keywords > 0:
        return queue[:max_keywords]
    return queue


job.effective_keywords = _capped_effective_keywords


if __name__ == "__main__":
    raise SystemExit(job.main())
