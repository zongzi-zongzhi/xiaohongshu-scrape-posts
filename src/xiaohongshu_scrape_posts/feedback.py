from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .paths import OUTPUTS_DIR


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


OUT_DIR = OUTPUTS_DIR
PROFILE_JSON = OUT_DIR / "xhs_no_reply_filter_profile_latest.json"
POINTER_JSON = OUT_DIR / "xhs_insforge_master_pointer.json"

FIXED_BASE_TOKEN = os.environ.get("XHS_LARK_BASE_TOKEN", "").strip()
FIXED_TABLE_ID = os.environ.get("XHS_LARK_TABLE_ID", "").strip()

FIELD_TIME = "发布时间"
FIELD_TITLE = "帖子名字"
FIELD_LINK = "帖子链接"
FIELD_COMMENT = "评论"
FIELD_KEYWORDS = "匹配关键词"
FIELD_REMARK = "备注"
FIELD_STATUS = "状态"
FIELD_OTHER = "其他"

NO_REPLY_STATUS = "不需要回"
POSITIVE_STATUSES = ("已回", "已评论")
TZ = dt.timezone(dt.timedelta(hours=8))

NOTE_ID_RE = re.compile(r"/(?:explore|discovery/item)/([0-9a-f]{24})")
MARKDOWN_URL_RE = re.compile(r"\((https?://[^)]+)\)")


def load_pointer(path: Path = POINTER_JSON) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def configure_fixed_master(pointer: dict[str, Any] | None = None) -> None:
    global FIXED_BASE_TOKEN, FIXED_TABLE_ID
    pointer = pointer if pointer is not None else load_pointer()
    FIXED_BASE_TOKEN = FIXED_BASE_TOKEN or str(pointer.get("fixed_master_base_token") or "").strip()
    FIXED_TABLE_ID = FIXED_TABLE_ID or str(
        pointer.get("fixed_master_table_id") or pointer.get("source_feishu_table_id") or ""
    ).strip()
    missing = [
        name
        for name, value in (
            ("XHS_LARK_BASE_TOKEN", FIXED_BASE_TOKEN),
            ("XHS_LARK_TABLE_ID", FIXED_TABLE_ID),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing fixed Feishu Base configuration. Set "
            + ", ".join(missing)
            + " or provide them in outputs/xhs_insforge_master_pointer.json."
        )

HELP_OR_PAIN_RE = re.compile(
    r"(求助|请教|提问|求解|疑问|问题|怎么办|咋办|怎么|如何|有木有|有没有|能教|分享下|求推荐|"
    r"不知何去何从|力不从心|很虚|卡住|卡壳|卡在|失败|翻车|踩坑|坑|报错|"
    r"超出限制|额度|没额度|清空数据|数据.*没了|浏览器.*没了|代码质量|review|Review|生产端|"
    r"发自内心的疑问)"
)
INSFORGE_RELEVANT_RE = re.compile(
    r"(后端|数据库|数据保存|数据表|登录|注册|鉴权|权限|RLS|Auth|auth|API Key|api key|密钥|"
    r"部署|上线|公网|Vercel|Supabase|Firebase|BaaS|Postgres|存储|长期用|长期保存)"
)
PURE_TUTORIAL_TITLE_RE = re.compile(
    r"(保姆级教程|中文教程|实用教程|教程|使用手册|手册|速成|精通|入门|嘴对嘴教学|包教包会|"
    r"Day\s*\d+|黑马Day|打卡|收藏笔记|拿走不谢|配享太庙|学懂AI|逼自己练完)"
)
NEWS_OR_LIST_TITLE_RE = re.compile(
    r"(每日AI资讯|AI资讯|今日GitHub热榜|GitHub热榜|GitHub爆火|热榜|项目榜|热门项目|热门Skills|"
    r"AI热门Skills|热门\s*Skill|日报|周报|新规发布|封号|全面包场|有什么区别|"
    r"上下文工程|模型.*发布)"
)
SOCIAL_OR_JOBLIKE_TITLE_RE = re.compile(r"(学习搭子|集合|找技术搭子|投合合信息|谁也别拦我投)")
PURE_TOOL_OR_PROMO_TITLE_RE = re.compile(
    r"(AI操作分享|一个接口连接多个AI模型|全自动Agent交付平台|开源了|SQL使用手册|字节内部.*手册|"
    r"宝藏插件|必备.*插件|保姆级教程|手把手从零搭建|Stripe\s*Startups|Build\s*Day|"
    r"项目管理不会消失|项目经理可能会|We'?re\s*hiring|hiring|月入|赚到钱|钱包|学习路线|学习资料|闭眼入|"
    r"飞书学SQL|Agent入门|通俗解释|文科论文|突然加速|个人网站～|有趣个人网站|开放接口给第三方模型|爱了爱了|"
    r"公式化提示词|千赞图文|排名上升太快|独立开发为什么最耗时|产品的阶段理解|"
    r"活动思考|沙龙|随记|又找到新东西|下载源代码|AI协助写作|底层思维|"
    r"AI\s*团队|开源一套|工具榜单|保姆级.*教程|热点日报|前端Skill|"
    r"排行榜|Skill排行榜|工具清单|音乐教师|AI工具清单|什么是大语言模型|"
    r"前端小特效|30s学会|入门到最佳实践|配置清单|一键提升vib.*能力|"
    r"黑马|花\s*2w|跨专业.*学习ai|学术论文|提示词|提示词模板|"
    r"AI还能这么玩|项目太有意思|设计师|设计感|PDF/Word.*Markdown|"
    r"黑客松|参赛|AI\s*Club|活动AI作战台|外滩黑客松|"
    r"AI\s*Workflow是什么|企业需要它|效率小工具|宝藏记录APP|免费积分|"
    r"零基础AI编程100讲|请求和响应|什么是配置文件|"
    r"GitHub\s*AI\s*热门项目|今日\s*GitHub|TOP5|排名|海外社媒|"
    r"YC手把手|亲测有效|基础知识（?1）?|直接上你桌面|"
    r"不用养Chrome|接入codex.*回不去了|数字后端进步最快|AI会议软件.*漏)"
)

OBSERVED_TERMS = [
    "教程",
    "入门",
    "手册",
    "热榜",
    "项目榜",
    "热门Skills",
    "资讯",
    "日报",
    "周报",
    "打卡",
    "学习搭子",
    "集合",
    "保姆级",
    "嘴对嘴",
    "包教包会",
    "拿走不谢",
    "配享太庙",
    "模型",
    "上下文",
    "封号",
    "投递",
    "实习",
    "求职",
    "面试",
    "岗位",
    "训练营",
    "课程",
]

KEYWORD_PROBE_TERMS = [
    "workbuddy",
    "WorkBuddy",
    "WorkBuddy 踩坑",
    "WorkBuddy 后端",
    "WorkBuddy 数据库",
    "WorkBuddy 配置 麻烦",
    "WorkBuddy 数据保存",
    "AI 做APP 数据保存",
    "AI 做网站 数据保存",
    "AI 项目 后端",
    "AI 项目 数据库",
    "AI 项目 上线失败",
    "AI 项目 部署失败",
    "AI 项目 登录注册",
    "AI 项目 登录权限",
    "AI 项目 API Key",
    "AI 项目 环境变量",
    "AI 项目 数据存不进去",
    "AI Coding 后端",
    "AI Coding 数据库",
    "AI Coding 部署失败",
    "AI Coding API Key",
    "AI Coding 环境变量",
    "Vibe Coding 后端",
    "vibe coding 后端",
    "vibe coding 数据库",
    "vibe coding 数据保存",
    "Cursor 后端",
    "Cursor 数据库",
    "Cursor Supabase",
    "Cursor 部署失败",
    "Cursor API Key",
    "Cursor 环境变量",
    "Claude Code 后端",
    "Claude Code 数据库",
    "Claude Code Supabase",
    "Claude Code 部署失败",
    "Claude Code API Key",
    "Claude Code 环境变量",
    "Trae 后端",
    "Trae 数据库",
    "Trae 部署失败",
    "Lovable 后端",
    "Lovable 数据库",
    "Lovable Supabase",
    "Bolt 后端",
    "Bolt 数据库",
    "Bolt Supabase",
    "Vercel 部署失败",
    "Vercel Supabase",
    "Vercel API Key",
    "Vercel 环境变量",
    "Vercel 环境变量 麻烦",
    "Vercel 配置 麻烦",
    "Supabase auth",
    "Supabase Auth 登录",
    "Supabase RLS 权限",
    "Supabase 数据保存",
    "Supabase 配置 麻烦",
    "Supabase 手动配置",
    "Supabase 不想配置",
    "Supabase 登录权限",
    "Supabase 环境变量",
    "Supabase API Key",
    "Supabase Edge Function",
    "Supabase 小白",
    "Supabase 踩坑",
    "Auth 配置 麻烦",
    "RLS 配置 麻烦",
    "API Key 配置 麻烦",
    "数据库 配置 麻烦",
    "后端 配置 麻烦",
    "登录权限 配置 麻烦",
    "手动配置 后端",
    "手动配置 数据库",
    "手动配置 权限",
    "手动配置 API Key",
    "不想配数据库",
    "不想配权限",
    "不想配 Supabase",
    "不想自己搭后端",
    "手动配置",
    "不想配置",
    "不想自己干",
    "繁琐",
    "麻烦",
    "折腾",
    "独立开发 后端",
    "独立开发 数据库",
    "独立开发 登录注册",
    "教程",
    "入门",
    "打卡",
    "热榜",
    "项目榜",
    "工具推荐",
    "工具清单",
    "学习资料",
    "课程",
]


def parse_json_output(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def run_lark(args: list[str], *, retries: int = 2) -> dict[str, Any]:
    cmd = ["lark-cli.cmd", *args, "--as", "user", "--format", "json"]
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
        if proc.returncode == 0:
            return parse_json_output(proc.stdout)
        merged = f"{proc.stdout}\n{proc.stderr}"
        if "1254291" in merged and attempt < retries:
            time.sleep(2 + attempt)
            continue
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{merged}")
    raise RuntimeError("unreachable")


def cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(text for item in value if (text := cell_text(item))).strip()
    if isinstance(value, dict):
        for key in ("text", "name", "value", "link", "url"):
            if key in value and (text := cell_text(value[key])):
                return text
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def note_key(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    markdown_match = MARKDOWN_URL_RE.search(text)
    if markdown_match:
        text = markdown_match.group(1)
    match = NOTE_ID_RE.search(text)
    if match:
        return match.group(1)
    return text.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def fetch_fixed_master_rows(
    *,
    base_token: str | None = None,
    table_id: str | None = None,
    limit: int = 200,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    configure_fixed_master()
    base_token = base_token or FIXED_BASE_TOKEN
    table_id = table_id or FIXED_TABLE_ID
    rows: list[dict[str, str]] = []
    pages: list[dict[str, Any]] = []
    offset = 0
    while True:
        result = run_lark(
            [
                "base",
                "+record-list",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--limit",
                str(limit),
                "--offset",
                str(offset),
            ]
        )
        data = result.get("data", {}) if isinstance(result, dict) else {}
        fields = data.get("fields") or []
        values = data.get("data") or []
        has_more = bool(data.get("has_more"))
        pages.append({"offset": offset, "count": len(values), "has_more": has_more})
        for value_row in values:
            if not isinstance(value_row, list):
                continue
            rows.append(
                {
                    str(fields[index]): cell_text(value_row[index]) if index < len(value_row) else ""
                    for index in range(len(fields))
                }
            )
        if not has_more or not values:
            break
        offset += len(values)
    return rows, pages


def no_reply_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if NO_REPLY_STATUS in str(row.get(FIELD_STATUS) or "")]


def positive_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if any(status in str(row.get(FIELD_STATUS) or "") for status in POSITIVE_STATUSES)]


def row_blob(row: dict[str, Any]) -> str:
    return "\n".join(
        str(row.get(field) or "")
        for field in (
            FIELD_TITLE,
            "title",
            "帖子标题",
            "帖子正文",
            "帖子正文部分",
            "desc",
            "description",
            FIELD_KEYWORDS,
            "keyword",
            FIELD_REMARK,
            FIELD_OTHER,
        )
    )


def parse_row_date(row: dict[str, Any]) -> dt.date | None:
    raw = str(row.get(FIELD_TIME) or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(raw[: len(fmt)], fmt).date()
        except ValueError:
            continue
    match = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if match:
        return dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def keyword_tokens(row: dict[str, Any]) -> list[str]:
    text = str(row.get(FIELD_KEYWORDS) or "").strip()
    values = [part.strip() for part in re.split(r"[,，、;；|/\n]+", text) if part.strip()]
    if not values and text:
        values = [text]
    blob = row_blob(row)
    for term in KEYWORD_PROBE_TERMS:
        if term.lower() in blob.lower():
            values.append(term)
    return list(dict.fromkeys(values))


def keyword_feedback_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    total: collections.Counter[str] = collections.Counter()
    no_reply: collections.Counter[str] = collections.Counter()
    positive: collections.Counter[str] = collections.Counter()
    no_reply_dates: dict[str, set[str]] = collections.defaultdict(set)
    positive_dates: dict[str, set[str]] = collections.defaultdict(set)
    today = dt.datetime.now(TZ).date()
    recent_days = [(today - dt.timedelta(days=offset)).isoformat() for offset in range(3)]

    for row in rows:
        status = str(row.get(FIELD_STATUS) or "")
        is_no_reply = NO_REPLY_STATUS in status
        is_positive = any(value in status for value in POSITIVE_STATUSES)
        if not is_no_reply and not is_positive:
            continue
        row_date = parse_row_date(row)
        date_key = row_date.isoformat() if row_date else ""
        for keyword in keyword_tokens(row):
            total[keyword] += 1
            if is_no_reply:
                no_reply[keyword] += 1
                if date_key:
                    no_reply_dates[keyword].add(date_key)
            if is_positive:
                positive[keyword] += 1
                if date_key:
                    positive_dates[keyword].add(date_key)

    per_keyword: dict[str, dict[str, Any]] = {}
    downweighted: dict[str, dict[str, Any]] = {}
    stopped: list[str] = []
    for keyword, count in total.items():
        nr = no_reply[keyword]
        pos = positive[keyword]
        no_reply_rate = nr / count if count else 0.0
        positive_rate = pos / count if count else 0.0
        consecutive_no_reply_days = all(day in no_reply_dates.get(keyword, set()) for day in recent_days)
        has_recent_positive = any(day in positive_dates.get(keyword, set()) for day in recent_days)
        payload = {
            "total": count,
            "no_reply": nr,
            "positive": pos,
            "no_reply_rate": round(no_reply_rate, 4),
            "positive_rate": round(positive_rate, 4),
            "recent_no_reply_days": sorted(no_reply_dates.get(keyword, set()) & set(recent_days)),
            "recent_positive_days": sorted(positive_dates.get(keyword, set()) & set(recent_days)),
        }
        per_keyword[keyword] = payload

        if count >= 3 and nr >= 2 and no_reply_rate >= 0.5 and pos == 0:
            reduction = 0.3 + min(0.3, (no_reply_rate - 0.5) * 0.6)
            downweighted[keyword] = {**payload, "reduction": round(reduction, 2)}
        if count >= 3 and nr >= 3 and consecutive_no_reply_days and not has_recent_positive:
            stopped.append(keyword)

    return {
        "per_keyword": dict(sorted(per_keyword.items(), key=lambda item: (item[1]["no_reply_rate"], item[1]["no_reply"]), reverse=True)),
        "downweighted_keywords": dict(sorted(downweighted.items(), key=lambda item: (item[1]["reduction"], item[1]["no_reply"]), reverse=True)),
        "stopped_keywords": sorted(stopped),
        "policy": {
            "downweight_rule": "If a keyword has >=3 feedback rows, >=2 no-reply rows, no_reply_rate>=0.5, and no positive rows, reduce its quota by 30%-60%.",
            "stop_rule": "If a keyword has no-reply feedback on each of the latest 3 dates and no recent positive feedback, stop crawling that keyword.",
            "positive_statuses": list(POSITIVE_STATUSES),
            "no_reply_status": NO_REPLY_STATUS,
        },
    }


def build_profile(rows: list[dict[str, str]], pages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    marked = no_reply_rows(rows)
    positives = positive_rows(rows)
    term_counts: collections.Counter[str] = collections.Counter()
    for row in marked:
        text = row_blob(row)
        for term in OBSERVED_TERMS:
            if term.lower() in text.lower():
                term_counts[term] += 1
    feedback = keyword_feedback_stats(rows)
    profile = {
        "generated_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "source": {
            "base_token": FIXED_BASE_TOKEN,
            "table_id": FIXED_TABLE_ID,
            "total_rows": len(rows),
            "pages": pages or [],
        },
        "status_value": NO_REPLY_STATUS,
        "positive_status_values": list(POSITIVE_STATUSES),
        "no_reply_count": len(marked),
        "positive_count": len(positives),
        "no_reply_note_ids": sorted({note_key(row.get(FIELD_LINK)) for row in marked if note_key(row.get(FIELD_LINK))}),
        "observed_term_counts": dict(term_counts.most_common()),
        "keyword_feedback": feedback.get("per_keyword", {}),
        "downweighted_keywords": feedback.get("downweighted_keywords", {}),
        "stopped_keywords": feedback.get("stopped_keywords", []),
        "keyword_policy": feedback.get("policy", {}),
        "samples": [
            {
                FIELD_TIME: row.get(FIELD_TIME, ""),
                FIELD_TITLE: row.get(FIELD_TITLE, ""),
                FIELD_LINK: row.get(FIELD_LINK, ""),
                FIELD_KEYWORDS: row.get(FIELD_KEYWORDS, ""),
                FIELD_STATUS: row.get(FIELD_STATUS, ""),
                FIELD_REMARK: row.get(FIELD_REMARK, ""),
            }
            for row in marked[:120]
        ],
        "rules": [
            "exact_no_reply_note_id",
            "keyword_downweight_30_to_60_percent",
            "keyword_stop_after_3_consecutive_no_reply_days",
            "pure_tutorial_without_help_or_pain",
            "news_or_listing_without_help_or_pain",
            "social_or_joblike_title",
            "pure_tool_or_promo_without_help_or_pain",
            "learned_terms_without_strong_lead_signal",
        ],
    }
    return profile


def write_profile(profile: dict[str, Any], path: Path = PROFILE_JSON) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cached_profile(path: Path = PROFILE_JSON) -> dict[str, Any]:
    if not path.exists():
        return {"enabled": False, "error": f"cache_missing:{path}"}
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"enabled": False, "error": f"cache_read_error:{type(exc).__name__}:{exc}"}
    if isinstance(profile, dict):
        profile["from_cache"] = True
        profile["enabled"] = bool(profile.get("no_reply_count", 0))
        return profile
    return {"enabled": False, "error": "cache_invalid"}


def load_no_reply_profile(*, refresh: bool = True, use_cache_on_error: bool = True) -> dict[str, Any]:
    if os.environ.get("XHS_NO_REPLY_FILTER", "").strip() in {"0", "false", "False", "off"}:
        return {"enabled": False, "disabled_by_env": True}
    if refresh:
        try:
            rows, pages = fetch_fixed_master_rows()
            profile = build_profile(rows, pages)
            profile["enabled"] = bool(profile.get("no_reply_count", 0))
            profile["from_cache"] = False
            write_profile(profile)
            return profile
        except Exception as exc:
            if not use_cache_on_error:
                raise
            cached = load_cached_profile()
            cached["refresh_error"] = f"{type(exc).__name__}: {exc}"
            return cached
    return load_cached_profile()


def has_help_or_strong_lead(row: dict[str, Any]) -> bool:
    text = row_blob(row)
    return bool(HELP_OR_PAIN_RE.search(text)) or (
        bool(INSFORGE_RELEVANT_RE.search(text)) and bool(re.search(r"(AI|ai|vibe|Vibe|Cursor|Claude|Codex|agent|Agent)", text))
    )


def explain_exclusion(row: dict[str, Any], profile: dict[str, Any] | None = None) -> tuple[bool, str]:
    profile = profile or {}
    if not profile.get("enabled"):
        return False, ""
    key = note_key(row.get(FIELD_LINK) or row.get("url") or row.get("帖子链接"))
    if key and key in set(profile.get("no_reply_note_ids") or []):
        return True, "exact_no_reply_note_id"

    title = str(row.get(FIELD_TITLE) or row.get("帖子标题") or row.get("title") or "").strip()
    text = row_blob(row)
    help_or_lead = has_help_or_strong_lead(row)

    if SOCIAL_OR_JOBLIKE_TITLE_RE.search(title):
        return True, "social_or_joblike_title"
    if NEWS_OR_LIST_TITLE_RE.search(title) and not help_or_lead:
        return True, "news_or_listing_without_help_or_pain"
    if PURE_TOOL_OR_PROMO_TITLE_RE.search(title) and not help_or_lead:
        return True, "pure_tool_or_promo_without_help_or_pain"
    if PURE_TUTORIAL_TITLE_RE.search(title) and not help_or_lead:
        return True, "pure_tutorial_without_help_or_pain"

    observed_counts = profile.get("observed_term_counts") or {}
    learned_terms = [term for term, count in observed_counts.items() if int(count or 0) >= 2 and term not in {"AI", "Vibe"}]
    learned_hits = [term for term in learned_terms if term.lower() in text.lower()]
    if len(learned_hits) >= 3 and not help_or_lead:
        return True, "learned_terms_without_strong_lead_signal:" + ",".join(learned_hits[:6])

    return False, ""


def should_exclude(row: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    excluded, _ = explain_exclusion(row, profile)
    return excluded


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and test dynamic Xiaohongshu no-reply filter profile from fixed Feishu Base.")
    parser.add_argument("--no-refresh", action="store_true", help="Use cached profile instead of reading Feishu.")
    parser.add_argument("--test-json", type=Path, help="Optional local JSON rows to test against the filter.")
    args = parser.parse_args()

    profile = load_no_reply_profile(refresh=not args.no_refresh)
    result: dict[str, Any] = {
        "profile_json": str(PROFILE_JSON),
        "enabled": bool(profile.get("enabled")),
        "from_cache": bool(profile.get("from_cache")),
        "no_reply_count": profile.get("no_reply_count", 0),
        "positive_count": profile.get("positive_count", 0),
        "observed_term_counts": profile.get("observed_term_counts", {}),
        "downweighted_keywords": profile.get("downweighted_keywords", {}),
        "stopped_keywords": profile.get("stopped_keywords", []),
        "refresh_error": profile.get("refresh_error", ""),
    }
    if args.test_json:
        data = json.loads(args.test_json.read_text(encoding="utf-8"))
        rows = data.get("rows", []) if isinstance(data, dict) else data
        rows = [row for row in rows if isinstance(row, dict)]
        excluded: list[dict[str, str]] = []
        for row in rows:
            is_excluded, reason = explain_exclusion(row, profile)
            if is_excluded:
                excluded.append(
                    {
                        FIELD_TITLE: str(row.get(FIELD_TITLE) or row.get("title") or "")[:120],
                        FIELD_LINK: str(row.get(FIELD_LINK) or row.get("url") or "")[:180],
                        "reason": reason,
                    }
                )
        result["test_rows"] = len(rows)
        result["test_excluded"] = len(excluded)
        result["test_excluded_sample"] = excluded[:40]
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
