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

job.BASE_START = datetime(2026, 8, 2, 0, 0, 0, tzinfo=TZ)
job.BASE_END = datetime.combine(datetime(2026, 8, 7).date(), dt_time(23, 59, 59), tzinfo=TZ)
job.INCREMENTAL_START = datetime(2026, 8, 7, 0, 0, 0, tzinfo=TZ)
job.INCREMENTAL_END = NOW
job.TARGET = None
job.KEEP_FIELDS = previous.OUTPUT_FIELDS

job.OLD_SOURCE_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260801_20260807.json"
job.OUT_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260802_20260808.json"
job.OUT_MD = job.OUT_DIR / "xhs_insforge_incremental_merged_20260802_20260808.md"
job.INBOX_MD = job.INBOX / "小红书建联线索池_新格式_增量合并_20260802-20260808.md"
job.FIELDS_JSON = job.WORK_DIR / "xhs_incremental_merged_base_fields_20260802_20260808.json"
job.RECORDS_JSON = job.WORK_DIR / "xhs_incremental_merged_records_payload_20260802_20260808.json"
job.INC_CACHE_JSON = job.OUT_DIR / "xhs_incremental_candidates_20260807_20260808.json"
job.DETAIL_CACHE_JSON = job.WORK_DIR / "xhs_incremental_detail_cache_20260807_20260808.json"
job.VERIFY_STATE_JSON = job.WORK_DIR / "xhs_incremental_verify_required_state_20260807_20260808.json"
job.VERIFY_SCREENSHOT = job.WORK_DIR / "xhs_incremental_verify_required_20260807_20260808.png"

WORKBUDDY_KEYWORDS = [
    "workbuddy",
    "WorkBuddy",
    "WorkBuddy 小白",
    "WorkBuddy 踩坑",
    "WorkBuddy 后端",
    "WorkBuddy 数据库",
]
HOTLIST_KEYWORD_RE = re.compile(r"(github\s*热榜|热榜)", re.IGNORECASE)
job.KEYWORDS = list(
    dict.fromkeys(
        [
            *WORKBUDDY_KEYWORDS,
            *[keyword for keyword in job.KEYWORDS if not HOTLIST_KEYWORD_RE.search(keyword)],
        ]
    )
)

STRICT_EXCLUDE = re.compile(
    r"(技术面|面试题|校招|秋招|春招|求职|简历|实习|招聘|招人|热招|在招|岗位|内推|投递|"
    r"办公地点|薪资|福利待遇|面经|offer|OFFER|训练营|课程售卖|"
    r"GitHub\s*热榜|github\s*热榜|GitHub热门项目|GitHub爆火|项目榜|每日\s*AI\s*项目推荐|"
    r"AI\s*开源热榜|开源热榜|热榜|热门Skills|AI热门Skills|热门\s*Skill|"
    r"Stripe\s*Startups|Build\s*Day|项目管理不会消失|项目经理可能会|"
    r"宝藏插件|必备.*插件|保姆级教程|手把手从零搭建|"
    r"We'?re\s*hiring|hiring|月入|赚到钱|钱包|学习路线|学习资料|闭眼入|"
    r"飞书学SQL|Agent入门|通俗解释|文科论文|突然加速|"
    r"个人网站～|有趣个人网站|开放接口给第三方模型|爱了爱了|"
    r"公式化提示词|千赞图文|排名上升太快|独立开发为什么最耗时|产品的阶段理解|"
    r"活动思考|沙龙|随记|又找到新东西|下载源代码|AI协助写作|底层思维|"
    r"AI\s*团队|开源一套|工具榜单|保姆级.*教程|热点日报|前端Skill|"
    r"排行榜|Skill排行榜|工具清单|音乐教师|AI工具清单|什么是大语言模型|"
    r"前端小特效|30s学会|入门到最佳实践|配置清单|一键提升vib.*能力|"
    r"不用养Chrome|接入codex.*回不去了|数字后端进步最快|AI会议软件.*漏)",
    re.IGNORECASE,
)
_base_hard_excluded = previous.hard_excluded


def strict_hard_excluded(row):
    return _base_hard_excluded(row) or bool(STRICT_EXCLUDE.search(previous._text_blob(row)))


previous.hard_excluded = strict_hard_excluded
job.expanded.hard_excluded = strict_hard_excluded


if __name__ == "__main__":
    raise SystemExit(job.main())
