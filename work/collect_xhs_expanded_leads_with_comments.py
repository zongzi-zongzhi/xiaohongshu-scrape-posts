from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright

import collect_xhs_since_last_crawl as base
from collect_xhs_since_title_body import extract_detail, md_escape, normalize_body


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
INBOX = Path(r"D:\czj note\00_Inbox")
WORK = ROOT / "work"

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
TODAY_START = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
SEVEN_DAY_START = TODAY_START - timedelta(days=6)

START_LABEL = SEVEN_DAY_START.strftime("%Y%m%d")
END_LABEL = TODAY_START.strftime("%Y%m%d")

TARGET = 100
MAX_DETAIL_FETCH = 120
AUTHOR_ROLL_LIMIT = 16
SEARCH_SCROLL_ROUNDS = 7

OUTPUT_JSON = OUT_DIR / f"xhs_insforge_expanded_leads_comments_7day_{START_LABEL}_{END_LABEL}.json"
OUTPUT_MD = OUT_DIR / f"xhs_insforge_expanded_leads_comments_7day_{START_LABEL}_{END_LABEL}.md"
INBOX_MD = INBOX / f"小红书建联线索池_评论方向_扩展口径_{START_LABEL}-{END_LABEL}.md"
LARK_FIELDS_JSON = WORK / "xhs_expanded_comment_base_fields.json"
LARK_RECORDS_JSON = WORK / "xhs_expanded_comment_records_payload.json"

SEED_FILES = [
    OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727_broad_raw.json",
    OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.json",
    OUT_DIR / "xhs_insforge_since_20260723_title_body_filtered.json",
    OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.json",
]

BASE_KEYWORDS = [
    "AI Coding 踩坑",
    "小白 AI Coding 踩坑",
    "AI 编程 踩坑",
    "AI Coding 小白",
    "Vibe Coding 踩坑",
    "Vibe Coding 小白",
    "vibecoding 踩坑",
    "vibe coding 后端",
    "vibe coding 数据库",
    "Cursor 踩坑",
    "Cursor 小白",
    "Cursor 后端",
    "Cursor 数据库",
    "Cursor Supabase",
    "AI 做 APP 后端",
    "AI 做网站 后端",
    "AI 做产品 后端",
    "AI 搭建网站 数据库",
    "AI Agent 后端",
    "AI Agent 数据库",
    "AI Agent MCP",
    "MCP 后端",
    "MCP 数据库",
    "Supabase AI 编程",
    "Supabase Vibe Coding",
    "Supabase Cursor",
    "Supabase 新手",
    "Supabase 小白",
    "Supabase 踩坑",
    "Supabase RLS 坑",
    "前端 操作数据库 安全",
    "API Key 泄露",
    "AI 编程 API Key",
    "密钥 泄露 独立开发",
    "独立开发 AI Coding",
    "独立开发 Vibe Coding",
    "独立开发 Cursor",
    "独立开发 Supabase",
    "零基础 Vibe Coding",
    "零基础 AI 做APP",
    "零基础 AI 编程 后端",
    "新手 Cursor 项目",
    "新手 Supabase 后端",
    "小白 Supabase 后端",
    "小白 做APP 数据库",
    "小白 后端 数据库",
    "后端 数据库 AI 编程",
    "AI 项目 数据库",
    "AI 项目 后端",
    "MVP AI Coding 后端",
    "MVP 数据库 Supabase",
]

LONG_TAIL_KEYWORDS = [
    "Claude Code 踩坑",
    "Claude Code 后端",
    "Claude Code 数据库",
    "Claude Code 部署",
    "Claude Code Supabase",
    "Trae 踩坑",
    "Trae 后端",
    "Trae 数据库",
    "Trae Supabase",
    "Trae 部署",
    "Lovable 后端",
    "Lovable Supabase",
    "Lovable 登录",
    "Lovable 部署",
    "Bolt 后端",
    "Bolt Supabase",
    "Bolt 部署",
    "v0 后端",
    "v0 Supabase",
    "v0 登录",
    "Coze 登录",
    "Coze Supabase",
    "Coze 工作流 后端",
    "Vercel 部署失败",
    "Vercel Supabase",
    "Vercel 数据库",
    "Vercel API Key",
    "localhost 部署",
    "AI 项目 上线失败",
    "AI 做小程序 登录",
    "AI 做小程序 数据库",
    "AI 做网站 数据保存",
    "AI 做APP 数据保存",
    "独立开发 登录注册",
    "独立开发 后端",
    "独立开发 数据库",
    "前端 API Key 暴露",
    "Cursor 部署",
    "Cursor API Key",
]

COMPETITOR_KEYWORDS = [
    "Firebase AI 编程",
    "Firebase 替代",
    "Firebase 后端",
    "Supabase 替代",
    "Supabase vs Firebase",
    "Supabase auth",
    "Supabase anon 权限",
    "Supabase 邮件",
    "Supabase Edge Function",
    "Supabase storage",
    "Supabase RLS 权限",
    "PocketBase AI 编程",
    "PocketBase 后端",
    "PocketBase 替代 Supabase",
    "Appwrite 后端",
    "Appwrite AI 编程",
    "NocoDB 数据库",
    "Baserow 数据库",
    "Zion 后端",
    "Zion vibecoding",
    "后端即服务",
    "BaaS 独立开发",
    "BaaS AI 编程",
    "OpenShip Supabase",
    "tinbase Supabase",
]

TOPIC_KEYWORDS = [
    "vibecoding",
    "AI新手村",
    "AI 编程 入门",
    "AI编程 学习打卡",
    "vibe coding 学习打卡",
    "小白 AI 编程 教程",
    "Cursor 教程",
    "Claude Code 教程",
    "Trae 教程",
    "Supabase 教程",
    "独立开发 打卡",
    "个人开发者",
    "AI编程",
    "独立开发",
    "howto用AI手搓APP",
    "howto入门vibecoding",
    "howto用好AI",
    "vibe coding 产品",
    "AI做APP",
    "AI做网站",
    "AI工具 推荐 编程",
    "AI 编程 工具推荐",
    "AI 编程 工具合集",
    "Cursor 工具推荐",
    "开发工具 推荐 AI",
    "GitHub 热榜 AI",
    "GitHub 热门 AI 编程",
    "GitHub 开源项目 数据库",
    "GitHub 开源项目 AI Agent",
    "开源项目 Supabase",
]

KEYWORDS = list(dict.fromkeys([*LONG_TAIL_KEYWORDS, *BASE_KEYWORDS, *COMPETITOR_KEYWORDS, *TOPIC_KEYWORDS]))

HARD_EXCLUDE_RE = re.compile(
    r"(实习|实习生|招聘|招人|招募|招生|内推|校招|社招|秋招|春招|求职|简历|面试|一面|二面|三面|终面|offer|"
    r"OFFER|HC|岗位|找工作|候选人|面经|入职|上岸|薪资|薪水|工资|应届|大厂|小厂|裁员|跳槽|外包|招前端|招后端|"
    r"leader|Leader|组里新来|新人入职|面完|被刷|AI岗|AI 岗|AI相关工作|AI 相关工作|就业|职业规划|转码|转行|"
    r"培训|课程|一门课|学员|报名|专场|公开课|体验课|训练营|陪跑|私教|资料包|资料领取|付费社群|网课|讲座|面了|应聘)"
)

AI_RE = re.compile(r"(AI|ai|AI Coding|AI编程|AI 编程|vibe coding|Vibe Coding|vibecoding|Cursor|Claude Code|Trae|Windsurf|Bolt|Lovable|Codex|Coze|v0|agent|Agent|MCP|mcp)")
BACKEND_RE = re.compile(r"(后端|数据库|数据保存|数据表|Supabase|supabase|Firebase|firebase|Postgres|postgres|SQL|sql|API|api|BaaS|后端即服务|PocketBase|Appwrite|NocoDB|Baserow|tinbase)")
AUTH_RE = re.compile(r"(登录|注册|鉴权|权限|RLS|rls|Auth|auth|Session|session|OAuth|oauth|anon|密钥|API Key|api key|Key|key|泄露|安全|环境变量)")
DEPLOY_RE = re.compile(r"(部署|上线|发布|公网|域名|Vercel|vercel|Netlify|Railway|Render|ECS|服务器|localhost|构建|生产环境)")
PAIN_RE = re.compile(r"(踩坑|避坑|坑|翻车|卡住|报错|失败|崩|血泪|复盘|不会|搞不懂|太难|求助|咋|怎么办|折磨|噩梦|大坑|坑点|踩过|卡壳)")
BUILD_RE = re.compile(r"(做APP|做 App|做app|做网站|小程序|搭建|手搓|项目|产品|MVP|mvp|独立开发|个人开发者|全栈|上线|发布)")
TOOLISH_RE = re.compile(r"(教程|指南|入门|速通|学习|打卡|工具|工具推荐|工具合集|宝藏工具|GitHub热门|Github热门|GitHub 热门|GitHub 热榜|开源项目|分享|推荐|清单|盘点|日报|周报|热榜)")
COMPETITOR_RE = re.compile(r"(Supabase|supabase|Firebase|firebase|PocketBase|Appwrite|Zion|NocoDB|Baserow|BaaS|后端即服务|tinbase|OpenShip|Vercel)")
LISTING_RE = re.compile(r"(日报|周报|热榜|今日热榜|热门项目|热门产品|Product Hunt|GitHub热门|Github热门|GitHub 热门|GitHub 热榜|开源项目|工具合集|工具推荐|宝藏网站|排行榜|清单|盘点|学习手册)")

AI_FLAVOR_RE = [
    re.compile(r"不是.+而是"),
    re.compile(r"不只是.+更是"),
    re.compile(r"真正"),
    re.compile(r"本质上"),
    re.compile(r"核心在于"),
    re.compile(r"总的来说"),
    re.compile(r"你觉得呢"),
    re.compile(r"赋能"),
    re.compile(r"闭环"),
]

FIELDS = [
    "发布时间",
    "帖子名字",
    "帖子链接",
    "匹配关键词",
    "评论方向",
    "评论例子",
    "帖主昵称",
    "帖主主页链接",
    "粉丝数",
    "联系方式",
    "帖子正文部分",
    "来源",
]


def parse_dt(value: Any, fallback_note_id: str = "") -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(TZ)
    if value:
        text = str(value).strip()
        if text:
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(TZ)
            except Exception:
                pass
    if fallback_note_id:
        return base.note_time(str(fallback_note_id or ""))
    return None


def format_dt(value: Any, fallback_note_id: str = "") -> str:
    dt = parse_dt(value, fallback_note_id)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def note_id_from_url(url: Any) -> str:
    match = re.search(r"/explore/([0-9a-f]{24})", str(url or ""))
    return match.group(1) if match else ""


def make_url(note_id: str, token: str = "") -> str:
    return base.make_url(note_id, token)


def clean_count(value: Any) -> int:
    return base.to_int(value)


def count_value(row: dict[str, Any], name: str) -> int:
    return int(row.get(name) or 0)


def engagement(row: dict[str, Any]) -> int:
    return count_value(row, "点赞") + count_value(row, "评论") * 3 + count_value(row, "收藏") * 2


def follower_sort_value(value: Any) -> int:
    return base.follower_sort_value(str(value or ""))


def source_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("rows", "posts", "records"):
        value = data.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def merge_keywords(old: Any, new: Any) -> str:
    values: list[str] = []
    for item in [old, new]:
        if isinstance(item, list):
            values.extend(str(v).strip() for v in item if str(v).strip())
        else:
            values.extend(str(v).strip() for v in str(item or "").split() if str(v).strip())
    deduped = list(dict.fromkeys(values))
    return " ".join(deduped[:20])


def normalize_candidate(raw: dict[str, Any], source: str) -> dict[str, Any] | None:
    note_id = str(raw.get("note_id") or raw.get("id") or note_id_from_url(raw.get("帖子链接") or raw.get("url"))).strip()
    if not note_id or "#" in note_id:
        return None
    published_at = parse_dt(raw.get("published_at"), note_id)
    if not published_at or published_at < SEVEN_DAY_START or published_at > NOW:
        return None

    title = str(raw.get("帖子名字") or raw.get("帖子标题") or raw.get("title") or "").strip()
    body = normalize_body(raw.get("帖子正文部分") or raw.get("desc") or raw.get("description") or "")
    token = str(raw.get("xsec_token") or raw.get("xsecToken") or "").strip()
    url = str(raw.get("帖子链接") or raw.get("url") or "").strip() or make_url(note_id, token)
    if not title or not url:
        return None

    author_id = str(raw.get("author_id") or raw.get("user_id") or "").strip()
    author_token = str(raw.get("author_xsec_token") or raw.get("author_xsecToken") or "").strip()
    profile_url = str(raw.get("帖主主页链接") or raw.get("profile_url") or "").strip()
    if not profile_url and author_id:
        profile_url = base.profile_home_url(author_id, author_token)

    return {
        "note_id": note_id,
        "published_at": published_at.isoformat(),
        "帖子名字": title,
        "帖子链接": url,
        "帖子正文部分": body,
        "点赞": clean_count(raw.get("点赞") or raw.get("liked_count") or raw.get("likedCount")),
        "评论": clean_count(raw.get("评论") or raw.get("comment_count") or raw.get("commentCount")),
        "收藏": clean_count(raw.get("收藏") or raw.get("collected_count") or raw.get("collectedCount")),
        "匹配关键词": merge_keywords(raw.get("matched_keywords"), raw.get("keyword")),
        "帖主昵称": str(raw.get("author") or raw.get("nickname") or raw.get("帖主昵称") or "").strip(),
        "author_id": author_id,
        "author_xsec_token": author_token,
        "帖主主页链接": profile_url,
        "粉丝数": str(raw.get("粉丝数") or "").strip(),
        "联系方式": str(raw.get("联系方式") or "").strip(),
        "来源": source,
        "detail_source": str(raw.get("detail_source") or ("seed_body" if body else "pending")),
    }


def add_candidate(candidates: dict[str, dict[str, Any]], row: dict[str, Any] | None) -> None:
    if not row:
        return
    existing = candidates.get(row["note_id"])
    if not existing:
        candidates[row["note_id"]] = row
        return
    if row.get("帖子正文部分") and not existing.get("帖子正文部分"):
        existing["帖子正文部分"] = row["帖子正文部分"]
        existing["detail_source"] = row.get("detail_source") or existing.get("detail_source")
    for field in ["帖子名字", "帖子链接", "帖主昵称", "author_id", "author_xsec_token", "帖主主页链接", "粉丝数", "联系方式"]:
        if row.get(field) and not existing.get(field):
            existing[field] = row[field]
    for field in ["点赞", "评论", "收藏"]:
        existing[field] = max(clean_count(existing.get(field)), clean_count(row.get(field)))
    existing["匹配关键词"] = merge_keywords(existing.get("匹配关键词"), row.get("匹配关键词"))
    if row.get("来源") and row["来源"] not in str(existing.get("来源") or ""):
        existing["来源"] = f"{existing.get('来源')};{row['来源']}"


def load_seed_candidates() -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for path in SEED_FILES:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"seed read error {path.name}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            continue
        before = len(candidates)
        for raw in source_rows(data):
            add_candidate(candidates, normalize_candidate(raw, path.name))
        print(f"seed {path.name}: +{len(candidates) - before}, total {len(candidates)}", flush=True)
    return candidates


def extract_items_from_search(page, keyword: str) -> list[dict[str, Any]]:
    return page.evaluate(
        """(keyword) => {
          const feeds = window.__INITIAL_STATE__?.search?.feeds;
          const arr = feeds?.value || feeds?._value || [];
          return Array.isArray(arr) ? arr.map((item) => {
            const nc = item.noteCard || item.note_card || {};
            const user = nc.user || {};
            const info = nc.interactInfo || nc.interact_info || {};
            return {
              id: item.id || nc.noteId || nc.note_id || '',
              xsec_token: item.xsecToken || item.xsec_token || '',
              title: nc.displayTitle || nc.title || '',
              desc: nc.desc || '',
              liked_count: info.likedCount || info.liked_count || '0',
              collected_count: info.collectedCount || info.collected_count || '0',
              comment_count: info.commentCount || info.comment_count || '0',
              author: user.nickname || user.nickName || '',
              author_id: user.userId || user.user_id || '',
              author_xsec_token: user.xsecToken || user.xsec_token || '',
              keyword,
            };
          }) : [];
        }""",
        keyword,
    )


def browser_context(playwright):
    profile_dir = os.environ.get("XHS_BROWSER_PROFILE_DIR")
    user_data_dir = Path(profile_dir) if profile_dir else Path.home() / ".xiaohongshu" / "browser-data-insforge-20260802"
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=True,
        proxy={"server": base.PROXY},
        viewport={"width": 1440, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        args=["--disable-blink-features=AutomationControlled", "--disable-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
        ignore_default_args=["--enable-automation"],
    )


def collect_live_search(candidates: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    with sync_playwright() as p:
        context = browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        for index, keyword in enumerate(KEYWORDS, start=1):
            print(f"search [{index}/{len(KEYWORDS)}] {keyword}", flush=True)
            url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_explore_feed"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4200, 6400))
                base.dismiss_login_popup(page)
                visible = page.evaluate("() => document.body.innerText.slice(0, 1000)")
                if "扫码验证身份" in visible or "保护账号安全" in visible:
                    failures.append({"keyword": keyword, "error": "verify_required"})
                    print("verify required during search", flush=True)
                    break
                stable_rounds = 0
                last_total = len(candidates)
                for _ in range(SEARCH_SCROLL_ROUNDS):
                    items = extract_items_from_search(page, keyword)
                    for item in items:
                        note_id = str(item.get("id") or "").strip()
                        published_at = parse_dt(None, note_id)
                        if not published_at or published_at < SEVEN_DAY_START or published_at > NOW:
                            continue
                        row = normalize_candidate(
                            {
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
                            },
                            "live_search",
                        )
                        add_candidate(candidates, row)
                    if len(candidates) == last_total:
                        stable_rounds += 1
                    else:
                        stable_rounds = 0
                    last_total = len(candidates)
                    if stable_rounds >= 2:
                        break
                    page.mouse.wheel(0, random.randint(1600, 2600))
                    page.wait_for_timeout(random.randint(850, 1500))
            except Exception as exc:
                failures.append({"keyword": keyword, "error": f"{type(exc).__name__}: {exc}"})
                print(f"search error {keyword}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if index % 20 == 0:
                snapshot = classify_and_select(list(candidates.values()), TARGET, fetch_ready=False)
                print(f"checkpoint candidates={len(candidates)} keepable={len(snapshot)}", flush=True)
            time.sleep(random.uniform(0.8, 1.8))
        context.close()
    return failures


def extract_profile_notes(page, source_author: dict[str, Any]) -> list[dict[str, Any]]:
    return page.evaluate(
        """(sourceAuthor) => {
          const out = [];
          const seen = new WeakSet();
          const idRe = /^[0-9a-f]{24}$/;
          function push(obj) {
            if (!obj || typeof obj !== 'object') return;
            const card = obj.noteCard || obj.note_card || obj;
            const id = obj.id || obj.noteId || obj.note_id || card.noteId || card.note_id || '';
            const title = card.displayTitle || card.title || obj.displayTitle || obj.title || '';
            if (!idRe.test(String(id)) || !String(title || '').trim()) return;
            const info = card.interactInfo || card.interact_info || obj.interactInfo || obj.interact_info || {};
            out.push({
              note_id: String(id),
              xsec_token: obj.xsecToken || obj.xsec_token || card.xsecToken || card.xsec_token || '',
              title: String(title),
              desc: card.desc || obj.desc || '',
              liked_count: info.likedCount || info.liked_count || '0',
              collected_count: info.collectedCount || info.collected_count || '0',
              comment_count: info.commentCount || info.comment_count || '0',
              author: sourceAuthor.author || '',
              author_id: sourceAuthor.author_id || '',
              author_xsec_token: sourceAuthor.author_xsec_token || '',
            });
          }
          function walk(obj, depth) {
            if (!obj || depth > 5) return;
            if (Array.isArray(obj)) {
              for (const item of obj.slice(0, 120)) {
                push(item);
                walk(item, depth + 1);
              }
              return;
            }
            if (typeof obj === 'object') {
              if (seen.has(obj)) return;
              seen.add(obj);
              push(obj);
              for (const value of Object.values(obj)) walk(value, depth + 1);
            }
          }
          walk(window.__INITIAL_STATE__ || {}, 0);
          const dedup = new Map();
          for (const item of out) if (!dedup.has(item.note_id)) dedup.set(item.note_id, item);
          return Array.from(dedup.values()).slice(0, 80);
        }""",
        {
            "author": source_author.get("帖主昵称") or "",
            "author_id": source_author.get("author_id") or "",
            "author_xsec_token": source_author.get("author_xsec_token") or "",
        },
    )


def collect_author_roll(candidates: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    authors: list[dict[str, Any]] = []
    seen_authors: set[str] = set()
    seeds = sorted(candidates.values(), key=lambda row: (score_raw(row), engagement(row)), reverse=True)
    for row in seeds:
        author_id = str(row.get("author_id") or "")
        if not author_id or author_id in seen_authors:
            continue
        seen_authors.add(author_id)
        authors.append(row)
        if len(authors) >= AUTHOR_ROLL_LIMIT:
            break
    if not authors:
        return failures
    print(f"author roll authors={len(authors)}", flush=True)
    with sync_playwright() as p:
        context = browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        for index, author in enumerate(authors, start=1):
            url = author.get("帖主主页链接") or base.profile_home_url(str(author.get("author_id") or ""), str(author.get("author_xsec_token") or ""))
            if not url:
                continue
            print(f"author [{index}/{len(authors)}] {author.get('帖主昵称') or author.get('author_id')}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4200, 6500))
                base.dismiss_login_popup(page)
                visible = page.evaluate("() => document.body.innerText.slice(0, 1600)")
                if "扫码验证身份" in visible or "保护账号安全" in visible:
                    failures.append({"author_id": str(author.get("author_id") or ""), "error": "verify_required"})
                    continue
                for _ in range(4):
                    for item in extract_profile_notes(page, author):
                        published_at = parse_dt(None, item.get("note_id"))
                        if not published_at or published_at < SEVEN_DAY_START or published_at > NOW:
                            continue
                        item["keyword"] = "author_roll"
                        item["published_at"] = published_at.isoformat()
                        add_candidate(candidates, normalize_candidate(item, "author_roll"))
                    page.mouse.wheel(0, random.randint(1600, 2600))
                    page.wait_for_timeout(random.randint(900, 1500))
            except Exception as exc:
                failures.append({"author_id": str(author.get("author_id") or ""), "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(random.uniform(2.0, 4.0))
        context.close()
    return failures


def text_blob(row: dict[str, Any]) -> str:
    return f"{row.get('帖子名字', '')}\n{row.get('帖子正文部分', '')}\n{row.get('匹配关键词', '')}"


def has(pattern: re.Pattern[str], row: dict[str, Any]) -> bool:
    return bool(pattern.search(text_blob(row)))


def hard_excluded(row: dict[str, Any]) -> bool:
    return bool(HARD_EXCLUDE_RE.search(text_blob(row)))


def classify(row: dict[str, Any]) -> tuple[str, str, str]:
    if hard_excluded(row):
        return "DROP", "", ""
    title = str(row.get("帖子名字") or "")
    ai = has(AI_RE, row)
    backend = has(BACKEND_RE, row)
    auth = has(AUTH_RE, row)
    deploy = has(DEPLOY_RE, row)
    pain = has(PAIN_RE, row)
    build = has(BUILD_RE, row)
    toolish = has(TOOLISH_RE, row)
    competitor = has(COMPETITOR_RE, row)
    listing = has(LISTING_RE, row)
    listing_title = bool(LISTING_RE.search(title))

    if listing_title and not (PAIN_RE.search(title) or AUTH_RE.search(title) or DEPLOY_RE.search(title) or BACKEND_RE.search(title)):
        return "C-轻互动", "P3", "先不提，等回复"

    if listing and not pain:
        if competitor and (ai or backend or deploy):
            return "C-轻互动", "P3", "先不提，等回复"
        if ai or backend or deploy or toolish:
            return "C-轻互动", "P3", "先不提，等回复"

    if pain and ai and (backend or auth or deploy or build):
        return "A-强痛点", "P1", "可以直接轻提"
    if pain and (backend or auth or deploy):
        return "A-强痛点", "P1", "可以直接轻提"
    if competitor and (ai or build or toolish or backend):
        return "B-潜在线索", "P2", "先共鸣，末尾轻提"
    if ai and (backend or auth or deploy or build):
        return "B-潜在线索", "P2", "先共鸣，末尾轻提"
    if toolish and (ai or backend or deploy or competitor):
        return "C-轻互动", "P3", "先不提，等回复"
    return "DROP", "", ""


def score_raw(row: dict[str, Any]) -> int:
    level, priority, _ = classify(row)
    if level == "DROP":
        return -999
    text = text_blob(row)
    base_score = {"A-强痛点": 300, "B-潜在线索": 200, "C-轻互动": 100}.get(level, 0)
    score = base_score
    for pattern, weight in [
        (PAIN_RE, 32),
        (AUTH_RE, 28),
        (DEPLOY_RE, 24),
        (BACKEND_RE, 20),
        (COMPETITOR_RE, 16),
        (AI_RE, 14),
        (BUILD_RE, 10),
        (TOOLISH_RE, 4),
    ]:
        if pattern.search(text):
            score += weight
    dt = parse_dt(row.get("published_at"), row.get("note_id", ""))
    if dt:
        score += max(0, 7 - (NOW - dt).days) * 3
    score += min(30, int(math.log10(max(1, engagement(row))) * 12))
    if priority == "P1":
        score += 12
    elif priority == "P2":
        score += 6
    return score


def classify_and_select(rows: list[dict[str, Any]], limit: int, fetch_ready: bool = True) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        level, priority, mention = classify(row)
        if level == "DROP":
            continue
        copied = dict(row)
        copied["线索等级"] = level
        copied["评论优先级"] = priority
        copied["是否直接提InsForge"] = mention
        copied["score"] = score_raw(copied)
        if fetch_ready and not copied.get("帖子正文部分"):
            copied["帖子正文部分"] = normalize_body(copied.get("帖子正文部分") or "")
        selected.append(copied)
    selected.sort(
        key=lambda row: (
            {"A-强痛点": 0, "B-潜在线索": 1, "C-轻互动": 2}.get(row.get("线索等级"), 9),
            {"P1": 0, "P2": 1, "P3": 2}.get(row.get("评论优先级"), 9),
            -int(row.get("score") or 0),
            -(parse_dt(row.get("published_at"), row.get("note_id", "")) or SEVEN_DAY_START).timestamp(),
        )
    )
    return selected[:limit]


def fetch_missing_bodies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending = [row for row in rows if not row.get("帖子正文部分")]
    if not pending:
        return rows
    pending = pending[:MAX_DETAIL_FETCH]
    print(f"detail pending={len(pending)}", flush=True)
    with sync_playwright() as p:
        context = browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        for index, row in enumerate(pending, start=1):
            print(f"detail [{index}/{len(pending)}] {row.get('note_id')} {row.get('帖子名字')}", flush=True)
            try:
                page.goto(row["帖子链接"], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4200, 6400))
                base.dismiss_login_popup(page)
                visible = page.evaluate("() => document.body.innerText.slice(0, 1200)")
                if "扫码验证身份" in visible or "保护账号安全" in visible:
                    row["帖子正文部分"] = normalize_body(row.get("帖子正文部分") or "（详情页触发安全验证，正文未完整获取）")
                    row["detail_source"] = "verify_required"
                elif "请求太频繁" in visible:
                    row["帖子正文部分"] = normalize_body(row.get("帖子正文部分") or "（详情页请求太频繁，正文未完整获取）")
                    row["detail_source"] = "too_frequent"
                else:
                    detail = extract_detail(page, {"note_id": row["note_id"], "帖子标题": row["帖子名字"], "desc": row.get("帖子正文部分", "")})
                    row["帖子名字"] = detail.get("title") or row["帖子名字"]
                    row["帖子正文部分"] = normalize_body(detail.get("body") or row.get("帖子正文部分") or "（未获取到正文）")
                    row["detail_source"] = detail.get("source") or "detail"
            except Exception as exc:
                row["帖子正文部分"] = normalize_body(row.get("帖子正文部分") or f"（详情页获取失败：{type(exc).__name__}）")
                row["detail_source"] = "error"
            if index % 12 == 0:
                time.sleep(random.uniform(14.0, 22.0))
            else:
                time.sleep(random.uniform(2.5, 5.0))
        context.close()
    return rows


def enrich_from_profile_cache(rows: list[dict[str, Any]]) -> None:
    cache = base.load_profile_cache()
    for row in rows:
        author_id = str(row.get("author_id") or "")
        if not author_id:
            row["粉丝数"] = row.get("粉丝数") or ""
            row["联系方式"] = row.get("联系方式") or "未发现"
            continue
        record = cache.get(author_id, {})
        body_text = str(record.get("body_text") or "")
        followers, contact = base.normalize_profile(record.get("profile"), body_text)
        if followers and followers != "获取失败" and not row.get("粉丝数"):
            row["粉丝数"] = followers
        if contact and contact not in {"获取失败", "未发现"}:
            row["联系方式"] = contact
        elif not row.get("联系方式"):
            row["联系方式"] = "未发现"
        if not row.get("帖主主页链接"):
            row["帖主主页链接"] = base.profile_home_url(author_id, str(row.get("author_xsec_token") or ""))


def comment_plan(row: dict[str, Any]) -> tuple[str, str]:
    text = text_blob(row).lower()
    level = row.get("线索等级", "")
    if "api key" in text or "密钥" in text or "泄露" in text or "安全" in text:
        return (
            "先认同安全提醒，把 key 暴露、权限和后端代理接起来，InsForge 只轻轻出现一次。",
            "这个提醒很该早点看到。AI 写 demo 的时候最容易图省事，把 key 和权限都塞进前端。InsForge 这种把登录、数据库、函数放一起的后端底座，适合先把密钥留在后端，少一点裸奔风险。",
        )
    if any(term in text for term in ["rls", "anon", "auth", "supabase", "firebase"]):
        return (
            "顺着对方的 Supabase/Firebase 配置经历聊，重点接住登录、权限策略、数据表这些新手高频坑。",
            "这个坑太常见了，AI 能把库连上，但登录、RLS、权限策略一细看就容易乱。我们做 InsForge 时也在补这块，想把认证、数据表和 API 的默认流程做顺一点，小项目别被配置卡太久。",
        )
    if any(term in text for term in ["localhost", "vercel", "railway", "render", "部署", "上线", "发布", "公网"]):
        return (
            "从“本地能跑”和“别人能稳定访问”的落差切入，再把部署、数据保存、登录放到同一条线上。",
            "localhost 这个太真实了。自己电脑能打开，发给朋友就没了，是很多小白第一次做 AI 项目都会遇到的坎。后面再加登录、数据保存，又是一层坑。我们做 InsForge 就是想把这些基础后端先接住，前期少被部署拖住。",
        )
    if any(term in text for term in ["登录", "注册", "鉴权", "session", "oauth"]):
        return (
            "把登录注册从“小功能”拉回到账号体系和后续返工成本，适合直接轻种草。",
            "登录注册看着小，真做起来最容易返工。尤其是 AI 先糊一个能跑的版本，后面接用户、权限、数据表就麻烦了。InsForge 现在把这些放在一套里，适合小项目先跑验证。",
        )
    if any(term in text for term in ["后端", "数据库", "数据保存", "数据表", "sql", "postgres"]):
        return (
            "回应“页面很快、后端磨人”的共识，讲清表结构、数据保存、接口是 AI 小项目常见卡点。",
            "前端出来得太快，后端反而更显眼：表怎么建、数据怎么存、API 怎么接。我们在做 InsForge，也是想把这几件事先兜住，让 AI 小项目别一到数据层就停下来。",
        )
    if any(term in text for term in ["z ion", "zion", "pocketbase", "appwrite", "openship", "tinbase", "baas", "后端即服务"]):
        return (
            "不硬怼竞品，顺着“轻后端/基础设施打包”的方向自然补充 InsForge。",
            "这个方向挺值得看，大家都在把数据库、登录、API 这些基础件往轻里收。我们做 InsForge 也差不多是这个思路，只是更偏 AI coding 项目开箱能用，先让 demo 变成能给别人试的版本。",
        )
    if any(term in text for term in ["github", "开源项目", "热榜", "日报", "工具合集", "工具推荐", "宝藏工具", "清单", "盘点"]):
        return (
            "低压互动，不急着推产品；先从榜单里的数据库、部署、权限工具切入，等对方回复后再介绍 InsForge。",
            "这个榜单可以顺着基础设施方向再挖一层，里面数据库、部署、权限相关的工具都值得单独拆出来看。先收藏了，后面想看看有没有更适合 AI 小项目的轻后端方案。",
        )
    if any(term in text for term in ["学习", "打卡", "教程", "入门", "速通", "指南"]):
        return (
            "把学习内容接到实操坑位上，先聊页面之后的登录、数据库、部署，不要一上来硬推。",
            "这类入门内容对小白挺友好。真动手做项目时，页面之后最容易卡在登录、数据库、部署这些基础件上。我们在做 InsForge，也是想让这一步轻一点，别学到一半被后端劝退。",
        )
    if level == "C-轻互动":
        return (
            "先正常互动，把话题往 AI 小项目的基础设施需求上带；InsForge 放到二次回复里讲。",
            "这个角度挺适合继续展开，很多 AI 小项目第一版做出来很快，但要给别人长期使用，就会碰到登录、数据保存、稳定访问这些问题。先收藏，后面想顺着这条线再研究一下。",
        )
    return (
        "先回应帖子里的具体经历，再轻带 InsForge 能帮小项目处理登录、数据和 API。",
        "这个坑挺典型的，AI 把页面做出来只是第一段路，登录、数据和 API 往往才开始卡。我们在做 InsForge，就是想先把这块垫稳一点，小项目验证时少绕路。",
    )


def audit_comment(text: str) -> list[str]:
    return [pattern.pattern for pattern in AI_FLAVOR_RE if pattern.search(text)]


def fill_comments(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    audit: dict[str, list[str]] = {}
    for row in rows:
        direction, comment = comment_plan(row)
        issues = audit_comment(comment)
        if issues:
            audit[str(row.get("帖子名字") or row.get("note_id"))] = issues
        row["评论方向"] = direction
        row["评论例子"] = comment
    return audit


def final_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "发布时间": format_dt(row.get("published_at"), row.get("note_id", "")),
        "帖子名字": row.get("帖子名字", ""),
        "帖子链接": row.get("帖子链接", ""),
        "匹配关键词": row.get("匹配关键词", ""),
        "评论方向": row.get("评论方向", ""),
        "评论例子": row.get("评论例子", ""),
        "帖主昵称": row.get("帖主昵称", ""),
        "帖主主页链接": row.get("帖主主页链接", ""),
        "粉丝数": row.get("粉丝数", ""),
        "联系方式": row.get("联系方式", "") or "未发现",
        "帖子正文部分": row.get("帖子正文部分", ""),
        "来源": row.get("来源", ""),
    }


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    final_rows = [final_row(row) for row in rows]

    lines = [
        "| " + " | ".join(FIELDS) + " |",
        "|" + "|".join(["---:" if field == "发布时间" else "---" for field in FIELDS]) + "|",
    ]
    for row in final_rows:
        cells = []
        for field in FIELDS:
            if field == "帖子链接" and row[field]:
                cells.append(f"[打开]({row[field]})")
            elif field == "帖主主页链接" and row[field]:
                cells.append(f"[打开]({row[field]})")
            else:
                cells.append(md_escape(row[field]))
        lines.append("| " + " | ".join(cells) + " |")
    markdown = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    try:
        INBOX_MD.write_text(markdown, encoding="utf-8")
        meta["inbox_md"] = str(INBOX_MD)
    except Exception as exc:
        fallback = OUT_DIR / INBOX_MD.name
        fallback.write_text(markdown, encoding="utf-8")
        meta["inbox_md"] = str(fallback)
        meta["inbox_write_error"] = f"{type(exc).__name__}: {exc}"

    LARK_FIELDS_JSON.write_text(
        json.dumps([{"name": field, "type": "text"} for field in FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    LARK_RECORDS_JSON.write_text(
        json.dumps({"fields": FIELDS, "rows": [[row.get(field, "") for field in FIELDS] for row in final_rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    payload = {"meta": meta, "rows": final_rows}
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    candidates = load_seed_candidates()
    print(f"loaded seeds total={len(candidates)}", flush=True)
    search_failures = collect_live_search(candidates)
    print(f"after live search total={len(candidates)} failures={len(search_failures)}", flush=True)
    author_failures = collect_author_roll(candidates)
    print(f"after author roll total={len(candidates)} failures={len(author_failures)}", flush=True)

    preselected = classify_and_select(list(candidates.values()), min(TARGET + 35, len(candidates)))
    fetch_missing_bodies(preselected)
    selected = classify_and_select(preselected, TARGET)
    enrich_from_profile_cache(selected)
    audit = fill_comments(selected)

    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "window_start": SEVEN_DAY_START.isoformat(),
        "window_end": NOW.isoformat(),
        "target": TARGET,
        "row_count": len(selected),
        "keywords_count": len(KEYWORDS),
        "keywords": KEYWORDS,
        "seed_files": [str(path) for path in SEED_FILES if path.exists()],
        "filter_change": "重新纳入学习打卡、泛教程、GitHub热榜、纯工具推荐；仍剔除招聘、实习、求职、课程售卖、训练营等不适合建联内容。",
        "sort_rule": "线索等级 A/B/C；同级按评论优先级、综合分、发布时间倒序",
        "product_basis": "InsForge 官网定位为 agent-native cloud infrastructure，包含 authentication、database、storage、edge functions、model gateway、realtime 等能力。",
        "search_failures": search_failures,
        "author_roll_failures": author_failures,
        "ai_flavor_audit_issues": audit,
    }
    write_outputs(selected, meta)
    levels = {}
    for row in selected:
        levels[row["线索等级"]] = levels.get(row["线索等级"], 0) + 1
    print(
        json.dumps(
            {
                "rows": len(selected),
                "levels": levels,
                "output_json": str(OUTPUT_JSON),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "lark_fields": str(LARK_FIELDS_JSON),
                "lark_records": str(LARK_RECORDS_JSON),
                "audit_issues": audit,
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
