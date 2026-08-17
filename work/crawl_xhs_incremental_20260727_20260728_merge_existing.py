from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright

import collect_xhs_expanded_leads_with_comments as expanded
import collect_xhs_since_last_crawl as base
from collect_xhs_since_title_body import extract_detail, normalize_body

try:
    import xhs_no_reply_filter
except Exception:  # Keep the crawl usable if the optional Lark filter module is unavailable.
    xhs_no_reply_filter = None

try:
    import xhs_lead_quality
except Exception:  # Keep the legacy crawl path usable if the quality module is unavailable.
    xhs_lead_quality = None

try:
    import xhs_rules_doc
except Exception:
    xhs_rules_doc = None


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
INBOX = Path(r"D:\czj note\00_Inbox")
RULES = xhs_rules_doc.RULES if xhs_rules_doc is not None else None

TZ = expanded.TZ
NOW = datetime.now(TZ)
BASE_START = datetime(2026, 7, 22, 0, 0, 0, tzinfo=TZ)
BASE_END = datetime.combine(BASE_START.date().replace(day=27), dt_time(23, 59, 59), tzinfo=TZ)
INCREMENTAL_START = datetime(2026, 7, 27, 0, 0, 0, tzinfo=TZ)
INCREMENTAL_END = NOW
TARGET: int | None = 100
DEFAULT_DAILY_INCREMENTAL_LIMIT = RULES.append_limit if RULES is not None else 50
DEFAULT_DAILY_INCREMENTAL_MIN = RULES.append_min if RULES is not None else 25
DEFAULT_KEYWORD_EXPANSION_STEP = 20
PAGE_WAIT_MIN_MS = 3200
PAGE_WAIT_MAX_MS = 5200
SCROLL_WAIT_MIN_MS = 850
SCROLL_WAIT_MAX_MS = 1350
KEYWORD_COOLDOWN_MIN_SECONDS = 0.8
KEYWORD_COOLDOWN_MAX_SECONDS = 1.6
DETAIL_WAIT_MIN_MS = 3600
DETAIL_WAIT_MAX_MS = 5600
DETAIL_COOLDOWN_MIN_SECONDS = 1.0
DETAIL_COOLDOWN_MAX_SECONDS = 2.0
VERIFY_COOLDOWN_MINUTES = 15

OLD_SOURCE_JSON = OUT_DIR / "xhs_insforge_minimal_full_body_20260721_20260727.json"
OUT_JSON = OUT_DIR / "xhs_insforge_incremental_merged_20260722_20260728.json"
OUT_MD = OUT_DIR / "xhs_insforge_incremental_merged_20260722_20260728.md"
INBOX_MD = INBOX / "小红书建联线索池_精简列_增量合并_20260722-20260728.md"
FIELDS_JSON = WORK_DIR / "xhs_incremental_merged_base_fields_20260722_20260728.json"
RECORDS_JSON = WORK_DIR / "xhs_incremental_merged_records_payload_20260722_20260728.json"
INC_CACHE_JSON = OUT_DIR / "xhs_incremental_candidates_20260727_20260728.json"
DETAIL_CACHE_JSON = WORK_DIR / "xhs_incremental_detail_cache.json"
VERIFY_STATE_JSON = WORK_DIR / "xhs_incremental_verify_required_state.json"
VERIFY_SCREENSHOT = WORK_DIR / "xhs_incremental_verify_required.png"

KEEP_FIELDS = RULES.output_fields if RULES is not None and RULES.output_fields else ["发布时间", "帖子名字", "帖子链接", "评论", "匹配关键词", "备注"]
NO_REPLY_PROFILE: dict[str, Any] | None = None

PRIORITY_KEYWORDS = [
    "workbuddy",
    "WorkBuddy",
    "WorkBuddy 踩坑",
    "WorkBuddy 后端",
    "WorkBuddy 数据库",
    "AI 做APP 数据保存",
    "AI 做网站 数据保存",
    "AI 搭建网站 数据库",
    "AI 项目 数据库",
    "AI 项目 后端",
    "AI 项目 上线失败",
    "AI 项目 部署失败",
    "AI 项目 登录注册",
    "AI Coding 后端",
    "AI Coding 数据库",
    "AI Coding 部署失败",
    "AI Coding 登录注册",
    "vibe coding 后端",
    "vibe coding 数据库",
    "vibe coding 数据保存",
    "vibe coding 登录注册",
    "Cursor 后端",
    "Cursor 数据库",
    "Cursor Supabase",
    "Claude Code 后端",
    "Claude Code 数据库",
    "Claude Code Supabase",
    "Trae 后端",
    "Trae 数据库",
    "Lovable 后端",
    "Lovable Supabase",
    "Bolt 后端",
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
    "Supabase Edge Function",
    "Supabase 小白 踩坑",
    "Supabase 踩坑",
    "Auth 配置 麻烦",
    "RLS 配置 麻烦",
    "API Key 配置 麻烦",
    "数据库 配置 麻烦",
    "后端 配置 麻烦",
    "不想自己搭后端",
    "Firebase 后端",
    "Supabase 替代",
    "PocketBase 后端",
    "独立开发 后端",
    "独立开发 数据库",
    "独立开发 登录注册",
    "独立开发 部署失败",
]
KEYWORDS = list(dict.fromkeys([*PRIORITY_KEYWORDS, *expanded.KEYWORDS]))


class VerifyRequired(RuntimeError):
    pass


def note_id_from_url(url: Any) -> str:
    match = re.search(r"/explore/([0-9a-f]{24})", str(url or ""))
    return match.group(1) if match else ""


def parse_row_dt(row: dict[str, Any]) -> datetime | None:
    note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or "")
    return expanded.parse_dt(row.get("published_at") or row.get("发布时间"), note_id)


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def merge_keywords(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        else:
            parts.extend(str(item).strip() for item in str(value or "").split() if str(item).strip())
    return " ".join(list(dict.fromkeys(parts))[:24])


def is_verify_text(text: str) -> bool:
    return any(marker in text for marker in ["扫码验证身份", "保护账号安全", "安全验证", "拖动滑块", "请完成验证"])


def capture_verify(page, stage: str, label: str) -> None:
    detected_at = datetime.now(TZ)
    try:
        page.screenshot(path=str(VERIFY_SCREENSHOT), full_page=True)
    except Exception:
        pass
    VERIFY_STATE_JSON.write_text(
        json.dumps(
            {
                "status": "verify_required",
                "stage": stage,
                "label": label,
                "url": page.url,
                "screenshot": str(VERIFY_SCREENSHOT),
                "detected_at": detected_at.isoformat(),
                "do_not_retry_before": (detected_at + timedelta(minutes=VERIFY_COOLDOWN_MINUTES)).isoformat(),
                "recovery": {
                    "policy": "Do not refresh captcha repeatedly. Stop the crawl, wait for cooldown, then scan once or switch to a newly logged-in profile.",
                    "safe_options": [
                        "wait_cooldown_and_open_visible_verification_once",
                        "switch_to_user_authorized_clean_profile",
                        "finalize_from_cache_without_feishu_write",
                    ],
                    "unsafe_options_to_avoid": [
                        "rapid_refresh_captcha",
                        "proxy_or_fingerprint_evasion",
                        "forged_or_synthetic_xhs_data",
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def save_incremental_cache(candidates: dict[str, dict[str, Any]], completed: set[int], failures: list[dict[str, str]]) -> None:
    active_keywords = effective_keywords(0)
    INC_CACHE_JSON.write_text(
        json.dumps(
            {
                "meta": {
                    "updated_at": datetime.now(TZ).isoformat(),
                    "window_start": INCREMENTAL_START.isoformat(),
                    "window_end": INCREMENTAL_END.isoformat(),
                    "candidate_count": len(candidates),
                    "completed_count": len(completed),
                    "keyword_count": len(active_keywords),
                    "keyword_policy": effective_keyword_policy(),
                },
                "completed_keyword_indexes": sorted(completed),
                "failures": failures,
                "candidates": list(candidates.values()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_incremental_cache() -> tuple[dict[str, dict[str, Any]], set[int], list[dict[str, str]]]:
    if not INC_CACHE_JSON.exists():
        return {}, set(), []
    try:
        data = json.loads(INC_CACHE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}, set(), []
    candidates = {row["note_id"]: row for row in data.get("candidates", []) if isinstance(row, dict) and row.get("note_id")}
    completed = {int(item) for item in data.get("completed_keyword_indexes", [])}
    failures = [item for item in data.get("failures", []) if isinstance(item, dict)]
    return candidates, completed, failures


def load_detail_cache() -> dict[str, dict[str, Any]]:
    if not DETAIL_CACHE_JSON.exists():
        return {}
    try:
        data = json.loads(DETAIL_CACHE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def save_detail_cache(cache: dict[str, dict[str, Any]]) -> None:
    DETAIL_CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    DETAIL_CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_detail_cache(rows: list[dict[str, Any]], cache: dict[str, dict[str, Any]]) -> None:
    for row in rows:
        note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or "")
        cached = cache.get(note_id)
        if not cached:
            continue
        body = normalize_body(cached.get("帖子正文部分") or cached.get("body") or "")
        if body:
            row["帖子正文部分"] = body
        if cached.get("帖子名字") and not row.get("帖子名字"):
            row["帖子名字"] = cached["帖子名字"]
        if cached.get("detail_source"):
            row["detail_source"] = cached["detail_source"]


def get_no_reply_profile() -> dict[str, Any]:
    global NO_REPLY_PROFILE
    if NO_REPLY_PROFILE is not None:
        return NO_REPLY_PROFILE
    if xhs_no_reply_filter is None:
        NO_REPLY_PROFILE = {"enabled": False, "error": "xhs_no_reply_filter_import_failed"}
        return NO_REPLY_PROFILE
    NO_REPLY_PROFILE = xhs_no_reply_filter.load_no_reply_profile(refresh=True, use_cache_on_error=True)
    print(
        json.dumps(
            {
                "no_reply_filter_enabled": bool(NO_REPLY_PROFILE.get("enabled")),
                "no_reply_count": NO_REPLY_PROFILE.get("no_reply_count", 0),
                "no_reply_profile_from_cache": bool(NO_REPLY_PROFILE.get("from_cache")),
                "no_reply_profile_refresh_error": NO_REPLY_PROFILE.get("refresh_error", ""),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return NO_REPLY_PROFILE


def effective_keywords(max_keywords: int = 0) -> list[str]:
    profile = get_no_reply_profile()
    if xhs_lead_quality is None:
        queue = KEYWORDS
    else:
        queue = xhs_lead_quality.build_keyword_queue(KEYWORDS, profile)
    if max_keywords > 0:
        return queue[:max_keywords]
    return queue


def effective_keyword_policy() -> dict[str, Any]:
    profile = get_no_reply_profile()
    all_keywords = list(dict.fromkeys(KEYWORDS))
    active = effective_keywords(0)
    policy = xhs_lead_quality.keyword_policy_summary(profile) if xhs_lead_quality is not None else {}
    policy["raw_keyword_count"] = len(all_keywords)
    policy["active_keyword_count"] = len(active)
    policy["low_intent_or_feedback_removed_count"] = max(0, len(all_keywords) - len(active))
    return policy


def no_reply_excluded(row: dict[str, Any]) -> bool:
    if xhs_no_reply_filter is None:
        return False
    profile = get_no_reply_profile()
    excluded, reason = xhs_no_reply_filter.explain_exclusion(row, profile)
    if excluded:
        row["no_reply_filter_reason"] = reason
    return excluded


def quality_select(rows: list[dict[str, Any]], limit: int, profile: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if xhs_lead_quality is None:
        selected = expanded.classify_and_select(rows, limit)
        return selected, {
            "enabled": False,
            "error": "xhs_lead_quality_import_failed",
            "input_count": len(rows),
            "selected_count": len(selected),
        }
    return xhs_lead_quality.select_candidates(rows, limit, profile)


def selection_cap(candidate_count: int, select_limit: int | None) -> int:
    if select_limit is None:
        return min(DEFAULT_DAILY_INCREMENTAL_LIMIT, candidate_count)
    if select_limit <= 0:
        return candidate_count
    return min(select_limit, candidate_count)


def select_filtered_incremental(
    rows: list[dict[str, Any]],
    *,
    select_limit: int | None,
    profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], int, int, int]:
    candidates_before_no_reply_filter = len(rows)
    filtered_rows = [row for row in rows if not no_reply_excluded(row)]
    no_reply_filtered_candidates = candidates_before_no_reply_filter - len(filtered_rows)
    select_count = selection_cap(len(filtered_rows), select_limit)
    selected_rows, quality_report = quality_select(filtered_rows, select_count, profile)
    before_final_hard_filter = len(selected_rows)
    selected_rows = [row for row in selected_rows if not expanded.hard_excluded(row)]
    final_hard_filtered = before_final_hard_filter - len(selected_rows)
    quality_report["final_hard_filtered"] = final_hard_filtered
    quality_report["daily_incremental_min"] = DEFAULT_DAILY_INCREMENTAL_MIN
    quality_report["daily_incremental_limit"] = DEFAULT_DAILY_INCREMENTAL_LIMIT
    quality_report["fallback_policy"] = (
        "If fewer than the daily minimum are found, expand to additional high-intent backend/deploy/database/config keywords; "
        "do not lower quality filters or include generic tool tutorials just to fill the quota."
    )
    return filtered_rows, selected_rows, quality_report, select_count, no_reply_filtered_candidates, final_hard_filtered


def apply_recent_filter(page) -> None:
    try:
        filter_btn = page.locator("div.filter")
        filter_btn.hover(timeout=5000)
        page.wait_for_selector("div.filter-panel", timeout=5000)
        panel = page.locator("div.filter-panel")
        for text in ["最新", "一周内"]:
            try:
                panel.get_by_text(text, exact=True).click(timeout=3000)
                page.wait_for_timeout(500)
            except Exception:
                pass
    except Exception:
        return


def collect_incremental(*, max_keywords: int, scroll_rounds: int, fresh: bool) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if fresh and INC_CACHE_JSON.exists():
        INC_CACHE_JSON.unlink()
    candidates, completed, failures = load_incremental_cache()
    keywords = effective_keywords(max_keywords)
    completed = {idx for idx in completed if idx <= len(keywords)}

    if len(completed) >= len(keywords):
        filtered = [
            row
            for row in candidates.values()
            if (dt := parse_row_dt(row)) and INCREMENTAL_START <= dt <= INCREMENTAL_END
            and not no_reply_excluded(row)
        ]
        return filtered, failures

    with sync_playwright() as p:
        context = expanded.browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        try:
            for index, keyword in enumerate(keywords, start=1):
                if index in completed:
                    continue
                print(f"search_incremental [{index}/{len(keywords)}] {keyword}", flush=True)
                try:
                    url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_explore_feed"
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(random.randint(PAGE_WAIT_MIN_MS, PAGE_WAIT_MAX_MS))
                    base.dismiss_login_popup(page)
                    visible = page.evaluate("() => document.body.innerText.slice(0, 1600)")
                    if is_verify_text(visible):
                        capture_verify(page, "search", keyword)
                        raise VerifyRequired(keyword)
                    apply_recent_filter(page)

                    stable_rounds = 0
                    last_total = len(candidates)
                    for _ in range(scroll_rounds):
                        items = expanded.extract_items_from_search(page, keyword)
                        for item in items:
                            note_id = str(item.get("id") or "").strip()
                            published_at = expanded.parse_dt(None, note_id)
                            if not published_at or published_at < INCREMENTAL_START or published_at > INCREMENTAL_END:
                                continue
                            raw = {
                                "note_id": note_id,
                                "xsec_token": item.get("xsec_token"),
                                "title": item.get("title"),
                                "desc": item.get("desc"),
                                "liked_count": item.get("liked_count"),
                                "comment_count": item.get("comment_count"),
                                "collected_count": item.get("collected_count"),
                                "author": item.get("author"),
                                "author_id": item.get("author_id"),
                                "author_xsec_token": item.get("author_xsec_token"),
                                "keyword": keyword,
                                "published_at": published_at.isoformat(),
                            }
                            row = expanded.normalize_candidate(raw, "live_incremental_20260727_20260728")
                            if row and no_reply_excluded(row):
                                continue
                            expanded.add_candidate(candidates, row)
                        stable_rounds = stable_rounds + 1 if len(candidates) == last_total else 0
                        last_total = len(candidates)
                        if stable_rounds >= 2:
                            break
                        page.mouse.wheel(0, random.randint(1400, 2400))
                        page.wait_for_timeout(random.randint(SCROLL_WAIT_MIN_MS, SCROLL_WAIT_MAX_MS))
                    completed.add(index)
                    save_incremental_cache(candidates, completed, failures)
                    print(f"checkpoint_incremental candidates={len(candidates)}", flush=True)
                except VerifyRequired:
                    save_incremental_cache(candidates, completed, failures)
                    raise
                except Exception as exc:
                    failures.append({"keyword": keyword, "index": str(index), "error": f"{type(exc).__name__}: {exc}"})
                    save_incremental_cache(candidates, completed, failures)
                    print(f"search_incremental_error {keyword}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                time.sleep(random.uniform(KEYWORD_COOLDOWN_MIN_SECONDS, KEYWORD_COOLDOWN_MAX_SECONDS))
        finally:
            context.close()

    filtered = [
        row
        for row in candidates.values()
        if (dt := parse_row_dt(row)) and INCREMENTAL_START <= dt <= INCREMENTAL_END
        and not no_reply_excluded(row)
    ]
    return filtered, failures


def fetch_incremental_bodies(rows: list[dict[str, Any]], *, limit: int | None = None) -> None:
    detail_cache = load_detail_cache()
    apply_detail_cache(rows, detail_cache)
    pending = [row for row in rows if not normalize_body(row.get("帖子正文部分"))]
    if limit is not None:
        pending = pending[:limit]
    if not pending:
        return

    with sync_playwright() as p:
        context = expanded.browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        try:
            for index, row in enumerate(pending, start=1):
                print(f"detail_incremental [{index}/{len(pending)}] {row.get('note_id')} {row.get('帖子名字')}", flush=True)
                try:
                    page.goto(row["帖子链接"], wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(random.randint(DETAIL_WAIT_MIN_MS, DETAIL_WAIT_MAX_MS))
                    base.dismiss_login_popup(page)
                    visible = page.evaluate("() => document.body.innerText.slice(0, 1600)")
                    if is_verify_text(visible):
                        capture_verify(page, "detail", str(row.get("帖子名字") or row.get("note_id") or ""))
                        raise VerifyRequired(str(row.get("note_id") or ""))
                    if "请求太频繁" in visible:
                        row["detail_source"] = "too_frequent"
                        continue
                    detail = extract_detail(page, {"note_id": row["note_id"], "帖子标题": row["帖子名字"], "desc": row.get("帖子正文部分", "")})
                    body = normalize_body(detail.get("body") or row.get("帖子正文部分") or "")
                    if body:
                        row["帖子正文部分"] = body
                    if detail.get("title"):
                        row["帖子名字"] = detail["title"]
                    row["detail_source"] = detail.get("source") or "detail"
                    note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or "")
                    if note_id:
                        detail_cache[note_id] = {
                            "note_id": note_id,
                            "帖子名字": str(row.get("帖子名字") or "").strip(),
                            "帖子链接": str(row.get("帖子链接") or "").strip(),
                            "帖子正文部分": normalize_body(row.get("帖子正文部分") or ""),
                            "detail_source": row.get("detail_source") or "",
                            "cached_at": datetime.now(TZ).isoformat(),
                        }
                        save_detail_cache(detail_cache)
                except VerifyRequired:
                    raise
                except Exception as exc:
                    row["detail_source"] = f"detail_error:{type(exc).__name__}"
                    print(f"detail_incremental_error {row.get('note_id')}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                time.sleep(random.uniform(DETAIL_COOLDOWN_MIN_SECONDS, DETAIL_COOLDOWN_MAX_SECONDS))
        finally:
            context.close()


def humanize_comment(comment: str) -> str:
    text = str(comment or "").strip()
    replacements = {
        "这个坑太常见了，AI 能把库连上，但登录、RLS、权限策略一细看就容易乱。我们做 InsForge 时也在补这块，想把认证、数据表和 API 的默认流程做顺一点，小项目别被配置卡太久。": "这个坑我也见过不少次，AI 能先把库连上，但登录、RLS、权限策略一细看就容易乱。InsForge 最近也在往这块补，认证、数据表和 API 尽量顺手一点，小项目别一直卡在配置上。",
        "这个提醒很该早点看到。AI 写 demo 的时候最容易图省事，把 key 和权限都塞进前端。InsForge 这种把登录、数据库、函数放一起的后端底座，适合先把密钥留在后端，少一点裸奔风险。": "这个提醒挺及时的。AI 写 demo 的时候很容易图省事，把 key 和权限塞到前端。InsForge 把登录、数据库、函数放在一起，至少能先把密钥留在后端，少一点裸奔风险。",
        "前端出来得太快，后端反而更显眼：表怎么建、数据怎么存、API 怎么接。我们在做 InsForge，也是想把这几件事先兜住，让 AI 小项目别一到数据层就停下来。": "前端出来太快，后端的问题反而更显眼：表怎么建、数据怎么存、API 怎么接。InsForge 想先把这几件事兜住，AI 小项目别一到数据层就停下来。",
        "localhost 这个太真实了。自己电脑能打开，发给朋友就没了，是很多小白第一次做 AI 项目都会遇到的坎。后面再加登录、数据保存，又是一层坑。我们做 InsForge 就是想把这些基础后端先接住，前期少被部署拖住。": "localhost 这个太真实了。自己电脑能打开，发给朋友就不行，很多小白第一次做 AI 项目都会撞到。后面再加登录、数据保存，又是一层坑。InsForge 就想先把这些基础后端接住，前期少被部署拖住。",
    }
    text = replacements.get(text, text)
    text = re.sub(r"不是(.{1,18})而是", r"\1之外，更要看", text)
    text = text.replace("本质上", "").replace("核心在于", "")
    text = text.replace("我们做 InsForge", "InsForge")
    return re.sub(r"\s+", " ", text).strip()


def make_incremental_final_row(row: dict[str, Any]) -> dict[str, Any]:
    dt = parse_row_dt(row)
    final = {
        "发布时间": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "",
        "帖子名字": str(row.get("帖子名字") or "").strip(),
        "帖子链接": str(row.get("帖子链接") or "").strip(),
        "评论": "",
        "匹配关键词": str(row.get("匹配关键词") or "").strip(),
        "备注": str(row.get("备注") or "").strip(),
        "note_id": row.get("note_id") or note_id_from_url(row.get("帖子链接")),
        "published_at": dt.isoformat() if dt else "",
        "来源": row.get("来源", ""),
    }
    if "评论例子" in KEEP_FIELDS:
        level, priority, mention = expanded.classify(row)
        copied = dict(row)
        copied["线索等级"] = level
        copied["评论优先级"] = priority
        copied["是否直接提InsForge"] = mention
        _, comment = expanded.comment_plan(copied)
        final["评论例子"] = humanize_comment(comment)
    body = normalize_body(row.get("帖子正文部分") or row.get("帖子正文") or "")
    if "帖子正文部分" in KEEP_FIELDS:
        final["帖子正文部分"] = body
    if "帖子正文" in KEEP_FIELDS:
        final["帖子正文"] = body
    return final


def load_old_rows() -> list[dict[str, Any]]:
    data = json.loads(OLD_SOURCE_JSON.read_text(encoding="utf-8"))
    source_rows = data.get("rows", [])
    rows: list[dict[str, Any]] = []
    for source_row in source_rows:
        if not isinstance(source_row, dict):
            continue
        note_id = note_id_from_url(source_row.get("帖子链接"))
        dt = parse_row_dt({"发布时间": source_row.get("发布时间"), "帖子链接": source_row.get("帖子链接"), "note_id": note_id})
        if not dt or not (BASE_START <= dt <= BASE_END):
            continue
        row = {field: str(source_row.get(field) or "").strip() for field in KEEP_FIELDS}
        row["note_id"] = note_id
        row["published_at"] = dt.isoformat()
        rows.append(row)
    return rows


def merge_rows(old_rows: list[dict[str, Any]], inc_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], prefer: bool = False) -> None:
        note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or row.get("帖子链接") or "")
        if not note_id:
            return
        existing = merged.get(note_id)
        if not existing:
            copied = dict(row)
            if "评论" in KEEP_FIELDS:
                copied["评论"] = ""
            if "备注" in KEEP_FIELDS:
                copied["备注"] = str(copied.get("备注") or "")
            merged[note_id] = copied
            return
        mergeable_fields = ["发布时间", "帖子名字", "帖子链接"]
        if "备注" in KEEP_FIELDS:
            mergeable_fields.append("备注")
        if "评论例子" in KEEP_FIELDS:
            mergeable_fields.append("评论例子")
        for field in mergeable_fields:
            if prefer and row.get(field):
                existing[field] = row[field]
            elif not existing.get(field) and row.get(field):
                existing[field] = row[field]
        if "评论" in KEEP_FIELDS:
            existing["评论"] = ""
        if "匹配关键词" in KEEP_FIELDS:
            existing["匹配关键词"] = merge_keywords(existing.get("匹配关键词"), row.get("匹配关键词"))
        body_field = "帖子正文部分" if "帖子正文部分" in KEEP_FIELDS else "帖子正文" if "帖子正文" in KEEP_FIELDS else ""
        if body_field:
            old_body = normalize_body(existing.get(body_field) or existing.get("帖子正文部分") or existing.get("帖子正文"))
            new_body = normalize_body(row.get("帖子正文部分") or row.get("帖子正文"))
            if new_body and (prefer or len(new_body) > len(old_body)):
                existing[body_field] = new_body
        if row.get("published_at"):
            existing["published_at"] = row["published_at"]

    for row in old_rows:
        add(row, prefer=False)
    for row in inc_rows:
        add(row, prefer=True)

    rows = list(merged.values())
    rows.sort(key=lambda row: parse_row_dt(row) or BASE_START, reverse=True)
    if TARGET is None or TARGET <= 0:
        return rows
    return rows[:TARGET]


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    final_rows = [{field: row.get(field, "") for field in KEEP_FIELDS} for row in rows]
    OUT_JSON.write_text(json.dumps({"meta": meta, "rows": final_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 小红书 InsForge 建联线索池（增量合并版）", ""]
    lines.append("| " + " | ".join(KEEP_FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(KEEP_FIELDS)) + " |")
    for row in final_rows:
        cells = []
        for field in KEEP_FIELDS:
            if field == "帖子链接" and row.get(field):
                cells.append(f"[打开]({row[field]})")
            else:
                cells.append(markdown_escape(row.get(field, "")))
        lines.append("| " + " | ".join(cells) + " |")
    markdown = "\n".join(lines) + "\n"
    OUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(markdown, encoding="utf-8")

    FIELDS_JSON.write_text(json.dumps([{"name": field, "type": "text"} for field in KEEP_FIELDS], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    RECORDS_JSON.write_text(
        json.dumps({"fields": KEEP_FIELDS, "rows": [[row.get(field, "") for field in KEEP_FIELDS] for row in final_rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> int:
    global TARGET
    global PAGE_WAIT_MIN_MS, PAGE_WAIT_MAX_MS, SCROLL_WAIT_MIN_MS, SCROLL_WAIT_MAX_MS
    global KEYWORD_COOLDOWN_MIN_SECONDS, KEYWORD_COOLDOWN_MAX_SECONDS
    global DETAIL_WAIT_MIN_MS, DETAIL_WAIT_MAX_MS, DETAIL_COOLDOWN_MIN_SECONDS, DETAIL_COOLDOWN_MAX_SECONDS

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-keywords", type=int, default=70)
    parser.add_argument("--scroll-rounds", type=int, default=4)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--detail-limit", type=int, default=None)
    parser.add_argument("--target", type=int, default=None, help="Final row cap. Use 0 or negative for no cap.")
    parser.add_argument("--select-limit", type=int, default=None, help="Incremental candidate selection cap. Use 0 or negative for all.")
    parser.add_argument("--min-daily-incremental", type=int, default=DEFAULT_DAILY_INCREMENTAL_MIN, help="Minimum high-quality incremental rows to aim for before writing outputs.")
    parser.add_argument("--keyword-expansion-step", type=int, default=DEFAULT_KEYWORD_EXPANSION_STEP, help="How many additional keywords to crawl when the daily minimum is not met.")
    parser.add_argument("--page-wait-min", type=int, default=None, help="Milliseconds to wait after opening a search page.")
    parser.add_argument("--page-wait-max", type=int, default=None, help="Milliseconds to wait after opening a search page.")
    parser.add_argument("--scroll-wait-min", type=int, default=None, help="Milliseconds to wait after each search scroll.")
    parser.add_argument("--scroll-wait-max", type=int, default=None, help="Milliseconds to wait after each search scroll.")
    parser.add_argument("--keyword-cooldown-min", type=float, default=None, help="Seconds to sleep after each keyword.")
    parser.add_argument("--keyword-cooldown-max", type=float, default=None, help="Seconds to sleep after each keyword.")
    parser.add_argument("--detail-wait-min", type=int, default=None, help="Milliseconds to wait after opening a detail page.")
    parser.add_argument("--detail-wait-max", type=int, default=None, help="Milliseconds to wait after opening a detail page.")
    parser.add_argument("--detail-cooldown-min", type=float, default=None, help="Seconds to sleep after each detail page.")
    parser.add_argument("--detail-cooldown-max", type=float, default=None, help="Seconds to sleep after each detail page.")
    args = parser.parse_args()

    if args.target is not None:
        TARGET = None if args.target <= 0 else args.target
    if args.page_wait_min is not None:
        PAGE_WAIT_MIN_MS = args.page_wait_min
    if args.page_wait_max is not None:
        PAGE_WAIT_MAX_MS = args.page_wait_max
    if args.scroll_wait_min is not None:
        SCROLL_WAIT_MIN_MS = args.scroll_wait_min
    if args.scroll_wait_max is not None:
        SCROLL_WAIT_MAX_MS = args.scroll_wait_max
    if args.keyword_cooldown_min is not None:
        KEYWORD_COOLDOWN_MIN_SECONDS = args.keyword_cooldown_min
    if args.keyword_cooldown_max is not None:
        KEYWORD_COOLDOWN_MAX_SECONDS = args.keyword_cooldown_max
    if args.detail_wait_min is not None:
        DETAIL_WAIT_MIN_MS = args.detail_wait_min
    if args.detail_wait_max is not None:
        DETAIL_WAIT_MAX_MS = args.detail_wait_max
    if args.detail_cooldown_min is not None:
        DETAIL_COOLDOWN_MIN_SECONDS = args.detail_cooldown_min
    if args.detail_cooldown_max is not None:
        DETAIL_COOLDOWN_MAX_SECONDS = args.detail_cooldown_max

    no_reply_profile = get_no_reply_profile()
    old_rows = load_old_rows()
    print(f"old_rows_{BASE_START:%Y%m%d}_{BASE_END:%Y%m%d}={len(old_rows)}", flush=True)

    try:
        active_keyword_count = len(effective_keywords(0))
        current_max_keywords = active_keyword_count if args.max_keywords <= 0 else min(args.max_keywords, active_keyword_count)
        min_daily_incremental = max(0, int(args.min_daily_incremental or 0))
        keyword_expansion_step = max(1, int(args.keyword_expansion_step or DEFAULT_KEYWORD_EXPANSION_STEP))
        keyword_expansion_events: list[dict[str, Any]] = []
        incremental_candidates, failures = collect_incremental(max_keywords=current_max_keywords, scroll_rounds=args.scroll_rounds, fresh=args.fresh)
        incremental_candidates, selected_incremental, quality_report, select_count, no_reply_filtered_candidates, final_hard_filtered = select_filtered_incremental(
            incremental_candidates,
            select_limit=args.select_limit,
            profile=no_reply_profile,
        )
        select_limit_allows_minimum = args.select_limit is None or args.select_limit <= 0 or args.select_limit >= min_daily_incremental
        while (
            min_daily_incremental
            and select_limit_allows_minimum
            and len(selected_incremental) < min_daily_incremental
            and current_max_keywords < active_keyword_count
        ):
            next_max_keywords = min(active_keyword_count, current_max_keywords + keyword_expansion_step)
            event: dict[str, Any] = {
                "reason": "daily_minimum_not_met",
                "selected_before": len(selected_incremental),
                "minimum": min_daily_incremental,
                "max_keywords_before": current_max_keywords,
                "max_keywords_after": next_max_keywords,
            }
            print(json.dumps({"keyword_expansion": event}, ensure_ascii=False), flush=True)
            current_max_keywords = next_max_keywords
            incremental_candidates, failures = collect_incremental(max_keywords=current_max_keywords, scroll_rounds=args.scroll_rounds, fresh=False)
            incremental_candidates, selected_incremental, quality_report, select_count, no_reply_filtered_candidates, final_hard_filtered = select_filtered_incremental(
                incremental_candidates,
                select_limit=args.select_limit,
                profile=no_reply_profile,
            )
            event["selected_after"] = len(selected_incremental)
            keyword_expansion_events.append(event)
        daily_min_target_met = not min_daily_incremental or len(selected_incremental) >= min_daily_incremental
        if final_hard_filtered:
            print(f"final_hard_filtered={final_hard_filtered}", flush=True)
        if not daily_min_target_met:
            print(
                json.dumps(
                    {
                        "daily_minimum_unmet": {
                            "selected": len(selected_incremental),
                            "minimum": min_daily_incremental,
                            "max_keywords_used": current_max_keywords,
                            "active_keyword_count": active_keyword_count,
                            "reason": "ran_out_of_active_keywords_or_quality_candidates",
                        }
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        print(f"incremental_candidates={len(incremental_candidates)} selected={len(selected_incremental)}", flush=True)
        requires_body = any(field in KEEP_FIELDS for field in ("帖子正文", "帖子正文部分"))
        if requires_body:
            fetch_incremental_bodies(selected_incremental, limit=args.detail_limit)
        else:
            print("detail_fetch_skipped=fields_do_not_require_body", flush=True)
    except VerifyRequired:
        print(json.dumps({"status": "verify_required", "state": str(VERIFY_STATE_JSON), "screenshot": str(VERIFY_SCREENSHOT)}, ensure_ascii=False, indent=2), flush=True)
        return 20

    inc_final = [make_incremental_final_row(row) for row in selected_incremental]
    merged = merge_rows(old_rows, inc_final)
    requires_body = any(field in KEEP_FIELDS for field in ("帖子正文", "帖子正文部分"))
    missing_body = sum(1 for row in merged if not normalize_body(row.get("帖子正文部分") or row.get("帖子正文"))) if requires_body else 0
    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "base_source": str(OLD_SOURCE_JSON),
        "base_window": {"start": BASE_START.isoformat(), "end": BASE_END.isoformat(), "rows": len(old_rows)},
        "incremental_window": {"start": INCREMENTAL_START.isoformat(), "end": INCREMENTAL_END.isoformat(), "candidates": len(incremental_candidates), "selected": len(inc_final)},
        "target": "unlimited" if TARGET is None else TARGET,
        "row_count": len(merged),
        "sort_rule": "按发布时间倒序；不截断条数；不硬凑。"
        if TARGET is None
        else f"按发布时间倒序；超过 {TARGET} 条时保留最新 {TARGET} 条；不硬凑。",
        "incremental_select_limit": "all" if args.select_limit is not None and args.select_limit <= 0 else select_count,
        "daily_incremental_min": min_daily_incremental,
        "daily_incremental_limit": DEFAULT_DAILY_INCREMENTAL_LIMIT,
        "daily_min_target_met": daily_min_target_met,
        "daily_min_policy": "目标每天新增写入飞书 25 到 50 条；不足 25 条时扩展关键词继续抓，但不降低质量标准、不用教程号或榜单内容凑数。",
        "fields": KEEP_FIELDS,
        "rules_doc": RULES.as_meta() if RULES is not None else {},
        "keywords_used": effective_keywords(current_max_keywords),
        "keywords_requested_initial": args.max_keywords,
        "keywords_requested_final": current_max_keywords,
        "active_keyword_count": active_keyword_count,
        "keyword_expansion_events": keyword_expansion_events,
        "keyword_policy": effective_keyword_policy(),
        "lead_quality": quality_report,
        "failures": failures,
        "no_reply_filter": {
            "enabled": bool(no_reply_profile.get("enabled")),
            "profile_json": str(xhs_no_reply_filter.PROFILE_JSON) if xhs_no_reply_filter is not None else "",
            "no_reply_count": no_reply_profile.get("no_reply_count", 0),
            "from_cache": bool(no_reply_profile.get("from_cache")),
            "refresh_error": no_reply_profile.get("refresh_error", ""),
            "filtered_candidates_after_cache": no_reply_filtered_candidates,
        },
        "missing_body_after": missing_body,
        "outputs": {
            "json": str(OUT_JSON),
            "markdown": str(OUT_MD),
            "inbox_markdown": str(INBOX_MD),
            "lark_fields": str(FIELDS_JSON),
            "lark_records": str(RECORDS_JSON),
        },
    }
    write_outputs(merged, meta)
    print(
        json.dumps(
            {
                "status": "complete",
                "rows": len(merged),
                "old_rows": len(old_rows),
                "incremental_selected": len(inc_final),
                "missing_body_after": missing_body,
                "output_json": str(OUT_JSON),
                "output_md": str(OUT_MD),
                "inbox_md": str(INBOX_MD),
                "lark_fields": str(FIELDS_JSON),
                "lark_records": str(RECORDS_JSON),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
