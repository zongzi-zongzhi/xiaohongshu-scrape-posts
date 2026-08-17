from __future__ import annotations

import sys
from datetime import datetime, time as dt_time

import crawl_xhs_incremental_20260727_20260728_merge_existing as job


TZ = job.TZ
NOW = datetime.now(TZ)

job.BASE_START = datetime(2026, 7, 23, 0, 0, 0, tzinfo=TZ)
job.BASE_END = datetime.combine(datetime(2026, 7, 28).date(), dt_time(23, 59, 59), tzinfo=TZ)
job.INCREMENTAL_START = datetime(2026, 7, 28, 0, 0, 0, tzinfo=TZ)
job.INCREMENTAL_END = NOW

job.OLD_SOURCE_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260722_20260728.json"
job.OUT_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260723_20260729.json"
job.OUT_MD = job.OUT_DIR / "xhs_insforge_incremental_merged_20260723_20260729.md"
job.INBOX_MD = job.INBOX / "小红书建联线索池_精简列_增量合并_20260723-20260729.md"
job.FIELDS_JSON = job.WORK_DIR / "xhs_incremental_merged_base_fields_20260723_20260729.json"
job.RECORDS_JSON = job.WORK_DIR / "xhs_incremental_merged_records_payload_20260723_20260729.json"
job.INC_CACHE_JSON = job.OUT_DIR / "xhs_incremental_candidates_20260728_20260729.json"
job.VERIFY_STATE_JSON = job.WORK_DIR / "xhs_incremental_verify_required_state_20260728_20260729.json"
job.VERIFY_SCREENSHOT = job.WORK_DIR / "xhs_incremental_verify_required_20260728_20260729.png"


if __name__ == "__main__":
    raise SystemExit(job.main())
