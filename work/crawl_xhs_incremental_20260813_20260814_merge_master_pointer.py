from __future__ import annotations

import os
import re
from datetime import datetime, time as dt_time

os.environ.setdefault("XHS_BROWSER_PROFILE_DIR", r"C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802")

import crawl_xhs_incremental_20260812_20260813_merge_master_pointer as previous


job = previous.job
TZ = job.TZ
NOW = datetime.now(TZ)

previous.OUTPUT_FIELDS = ["发布时间", "帖子名字", "帖子链接", "评论", "匹配关键词", "备注"]
previous.BODY_FIELD = "帖子正文"
previous.OLD_BODY_FIELD = "帖子正文部分"

job.BASE_START = datetime(2026, 8, 8, 0, 0, 0, tzinfo=TZ)
job.BASE_END = datetime.combine(datetime(2026, 8, 13).date(), dt_time(23, 59, 59), tzinfo=TZ)
job.INCREMENTAL_START = datetime(2026, 8, 13, 0, 0, 0, tzinfo=TZ)
job.INCREMENTAL_END = NOW
job.TARGET = None
job.KEEP_FIELDS = previous.OUTPUT_FIELDS

job.OLD_SOURCE_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260807_20260813.json"
job.OUT_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260808_20260814.json"
job.OUT_MD = job.OUT_DIR / "xhs_insforge_incremental_merged_20260808_20260814.md"
job.INBOX_MD = job.INBOX / "小红书建联线索池_新格式_增量合并_20260808-20260814.md"
job.FIELDS_JSON = job.WORK_DIR / "xhs_incremental_merged_base_fields_20260808_20260814.json"
job.RECORDS_JSON = job.WORK_DIR / "xhs_incremental_merged_records_payload_20260808_20260814.json"
job.INC_CACHE_JSON = job.OUT_DIR / "xhs_incremental_candidates_20260813_20260814.json"
job.DETAIL_CACHE_JSON = job.WORK_DIR / "xhs_incremental_detail_cache_20260813_20260814.json"
job.VERIFY_STATE_JSON = job.WORK_DIR / "xhs_incremental_verify_required_state_20260813_20260814.json"
job.VERIFY_SCREENSHOT = job.WORK_DIR / "xhs_incremental_verify_required_20260813_20260814.png"

WORKBUDDY_KEYWORDS = [
    "workbuddy",
    "WorkBuddy",
    "WorkBuddy 踩坑",
    "WorkBuddy 后端",
    "WorkBuddy 数据库",
]
HOTLIST_KEYWORD_RE = re.compile(r"(github\s*热榜|热榜|项目榜|榜单|日报|资讯)", re.IGNORECASE)
job.KEYWORDS = list(
    dict.fromkeys(
        [
            *WORKBUDDY_KEYWORDS,
            *[keyword for keyword in job.KEYWORDS if not HOTLIST_KEYWORD_RE.search(keyword)],
        ]
    )
)


if __name__ == "__main__":
    raise SystemExit(job.main())
