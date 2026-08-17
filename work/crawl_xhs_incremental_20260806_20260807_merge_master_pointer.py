from __future__ import annotations

import re
from datetime import datetime, time as dt_time

import crawl_xhs_incremental_20260731_20260801_merge_master_pointer as previous


job = previous.job
TZ = job.TZ
NOW = datetime.now(TZ)

previous.OUTPUT_FIELDS = ["发布时间", "帖子名字", "帖子链接", "评论", "匹配关键词", "备注"]
previous.BODY_FIELD = "帖子正文"
previous.OLD_BODY_FIELD = "帖子正文部分"

job.BASE_START = datetime(2026, 8, 1, 0, 0, 0, tzinfo=TZ)
job.BASE_END = datetime.combine(datetime(2026, 8, 6).date(), dt_time(23, 59, 59), tzinfo=TZ)
job.INCREMENTAL_START = datetime(2026, 8, 6, 0, 0, 0, tzinfo=TZ)
job.INCREMENTAL_END = NOW
job.TARGET = None
job.KEEP_FIELDS = previous.OUTPUT_FIELDS

job.OLD_SOURCE_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260731_20260806.json"
job.OUT_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260801_20260807.json"
job.OUT_MD = job.OUT_DIR / "xhs_insforge_incremental_merged_20260801_20260807.md"
job.INBOX_MD = job.INBOX / "小红书建联线索池_新格式_增量合并_20260801-20260807.md"
job.FIELDS_JSON = job.WORK_DIR / "xhs_incremental_merged_base_fields_20260801_20260807.json"
job.RECORDS_JSON = job.WORK_DIR / "xhs_incremental_merged_records_payload_20260801_20260807.json"
job.INC_CACHE_JSON = job.OUT_DIR / "xhs_incremental_candidates_20260806_20260807.json"
job.DETAIL_CACHE_JSON = job.WORK_DIR / "xhs_incremental_detail_cache_20260806_20260807.json"
job.VERIFY_STATE_JSON = job.WORK_DIR / "xhs_incremental_verify_required_state_20260806_20260807.json"
job.VERIFY_SCREENSHOT = job.WORK_DIR / "xhs_incremental_verify_required_20260806_20260807.png"

STRICT_EXCLUDE = re.compile(
    r"(技术面|面试题|校招|秋招|春招|求职|简历|实习|招聘|招人|热招|在招|岗位|内推|投递|"
    r"办公地点|薪资|福利待遇|面经|offer|OFFER|训练营|课程售卖)"
)
_base_hard_excluded = previous.hard_excluded


def strict_hard_excluded(row):
    return _base_hard_excluded(row) or bool(STRICT_EXCLUDE.search(previous._text_blob(row)))


previous.hard_excluded = strict_hard_excluded
job.expanded.hard_excluded = strict_hard_excluded


if __name__ == "__main__":
    raise SystemExit(job.main())
