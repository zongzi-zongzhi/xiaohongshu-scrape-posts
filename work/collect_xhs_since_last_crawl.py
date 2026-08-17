from __future__ import annotations

import csv
import json
import math
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
RAW_DIR = ROOT / "work" / "xhs_since_20260723_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

LAST_MD = Path(r"D:\czj note\00_Inbox\小红书痛点+建议评论方向_含帖主信息.md")
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书痛点+建议评论方向_新增_20260723-20260726.md")
OUTPUT_JSON = OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.json"
OUTPUT_MD = OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.md"
OUTPUT_CSV = OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.csv"
PROFILE_CACHE = OUT_DIR / "xhs_insforge_author_profiles_cache_since_20260723.json"

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
START_AT = datetime.fromtimestamp(LAST_MD.stat().st_mtime, tz=TZ)
TARGET = 100
PROXY = "http://127.0.0.1:18089"

KEYWORDS = [
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

EXCLUDE_RE = re.compile(
    r"(实习|实习生|招聘|招人|招募|招生|内推|校招|社招|秋招|春招|求职|简历|面试|一面|二面|三面|终面|offer|"
    r"OFFER|HC|岗位|找工作|候选人|面经|入职|上岸|薪资|薪水|工资|应届|大厂|小厂|裁员|跳槽|外包|招前端|招后端|"
    r"leader|Leader|组里新来|新人入职|面完|被刷|AI岗|AI 岗|AI相关工作|AI 相关工作|找不到.*工作|就业|"
    r"职业规划|转码|转行|培训|课程|学员|报名|专场|公开课|体验课)"
)

AI_TERMS = [
    "ai",
    "ai coding",
    "ai编程",
    "ai 编程",
    "vibe",
    "vibecoding",
    "cursor",
    "agent",
    "mcp",
    "claude code",
    "trae",
    "windsurf",
    "bolt",
    "lovable",
]

PAIN_TERMS = [
    "踩坑",
    "坑",
    "避坑",
    "翻车",
    "小白",
    "新手",
    "零基础",
    "不会",
    "搞不懂",
    "安全",
    "泄露",
    "报错",
    "卡住",
    "复盘",
    "怎么选",
    "选择",
    "连接",
    "部署",
    "上线",
    "怎么办",
]

BACKEND_TERMS = [
    "后端",
    "数据库",
    "supabase",
    "firebase",
    "postgres",
    "sql",
    "api",
    "api key",
    "密钥",
    "rls",
    "auth",
    "mcp",
    "全栈",
    "app",
    "网站",
    "mvp",
    "独立开发",
]

BUILD_TERMS = [
    "做app",
    "做 app",
    "做网站",
    "搭建",
    "手搓",
    "项目",
    "产品",
    "mvp",
    "上线",
    "部署",
    "全栈",
    "后端",
    "数据库",
    "登录",
    "auth",
    "api",
]

SOFT_EXCLUDE_RE = re.compile(
    r"(选题荒|内容创作|一周内容|视频项目|按场景选工具|工具推荐|工具合集|超强开源神器|最好用.*提示词|"
    r"提示词合集|资料包|粉色群|个人成长|市场情绪|行业新知|峰会|活动|大会|线下|直播|专场|AI视频|AI 视频)"
)

CONTACT_PATTERNS = [
    ("邮箱", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)),
    ("手机号", re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")),
    ("微信", re.compile(r"(?:微信|VX|vx|V信|v信|WeChat|wechat|wx|WX|加V|加v)[号：:\s]*([A-Za-z][A-Za-z0-9_-]{4,19})")),
    ("QQ", re.compile(r"(?:QQ|qq)[号：:\s]*([1-9]\d{4,11})")),
    ("公众号", re.compile(r"(?:公众号|公号|订阅号)[：:\s]*([^，。；;\s]{2,30})")),
]


def md_escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")


def note_time(note_id: str) -> datetime | None:
    if not re.match(r"^[0-9a-f]{24}$", note_id or ""):
        return None
    try:
        return datetime.fromtimestamp(int(note_id[:8], 16), tz=TZ)
    except Exception:
        return None


def to_int(value: Any) -> int:
    text = "" if value is None else str(value).strip().lower().replace(",", "")
    if not text:
        return 0
    multiplier = 1
    if text.endswith(("w", "万")):
        multiplier = 10000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else 0


def follower_sort_value(value: str) -> int:
    return to_int(value)


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def relevance_score(title: str, desc: str, keyword_text: str) -> int:
    haystack = f"{title} {desc} {keyword_text}".lower()
    if EXCLUDE_RE.search(title) or EXCLUDE_RE.search(desc):
        return -999

    has_ai = contains_any(haystack, AI_TERMS)
    has_backend = contains_any(haystack, BACKEND_TERMS)
    has_pain = contains_any(haystack, PAIN_TERMS)
    has_build = contains_any(haystack, BUILD_TERMS)
    has_supabase = "supabase" in haystack

    strong_need = (has_pain and (has_backend or has_build or has_supabase)) or (has_backend and has_build and has_ai)
    if not strong_need:
        return -999
    if SOFT_EXCLUDE_RE.search(title) or SOFT_EXCLUDE_RE.search(desc):
        return -999

    score = 0
    for term in AI_TERMS:
        if term.lower() in haystack:
            score += 5
    for term in PAIN_TERMS:
        if term.lower() in haystack:
            score += 4
    for term in BACKEND_TERMS:
        if term.lower() in haystack:
            score += 3
    if any(term in title for term in ["小白", "新手", "零基础"]):
        score += 9
    if any(term in title for term in ["踩坑", "避坑", "翻车", "卡住", "报错"]):
        score += 9
    if any(term in title.lower() for term in ["vibe", "cursor", "ai coding", "agent", "supabase"]):
        score += 7
    return score


def make_url(note_id: str, token: str) -> str:
    token_q = f"?xsec_token={token}&xsec_source=pc_search" if token else "?xsec_source=pc_search"
    return f"https://www.xiaohongshu.com/explore/{note_id}{token_q}"


def profile_home_url(user_id: str, xsec_token: str = "") -> str:
    if not user_id:
        return ""
    if xsec_token:
        return f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={xsec_token}&xsec_source=pc_search"
    return f"https://www.xiaohongshu.com/user/profile/{user_id}"


def compact_comment(row: dict[str, Any]) -> str:
    title = row["帖子标题"]
    text = f"{title} {row.get('desc','')}".lower()
    if "api key" in text or "密钥" in text or "泄露" in text or "安全" in text:
        return "这个坑真得早点管，AI 写得快的时候最容易把 key、权限这些塞乱。InsForge 可以先把登录、数据库、函数这些后端边界搭好，再让 AI 写业务，后面少补洞。"
    if "supabase" in text or "rls" in text or "auth" in text:
        return "Supabase 很强，但新手卡在 RLS、Auth、表结构上也挺常见。可以顺手看看 InsForge，它更偏 AI Coding 场景，把库、登录和接口先接稳。"
    if "数据库" in text or "sql" in text or "postgres" in text:
        return "数据这块一乱，前端再漂亮也只是 demo。我会建议先把数据库、登录和接口收住，InsForge 这种一体化后端就适合在这一步少踩坑。"
    if "部署" in text or "上线" in text or "mvp" in text or "产品" in text:
        return "从 demo 到能上线，最麻烦的经常不是页面，而是登录、数据、环境变量这些。InsForge 可以把这几块先搭起来，对小团队会省不少返工。"
    if "agent" in text or "mcp" in text:
        return "Agent 真要落地，不能只会写代码，还得能稳稳接后端资源。InsForge 就是往这个方向做的，让数据库、Auth、函数这些更容易被 AI 接上。"
    return "这个踩坑很真实，AI 写页面快，但一到数据、登录、后端就容易散。可以看看 InsForge，先把这些基础能力搭好，再继续 vibe 会稳很多。"


def extract_items_from_state(page, keyword: str) -> list[dict[str, Any]]:
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
              type: nc.type || '',
              liked_count: info.likedCount || info.liked_count || '0',
              collected_count: info.collectedCount || info.collected_count || '0',
              comment_count: info.commentCount || info.comment_count || '0',
              shared_count: info.sharedCount || info.shared_count || '0',
              author: user.nickname || user.nickName || '',
              author_id: user.userId || user.user_id || '',
              author_xsec_token: user.xsecToken || user.xsec_token || '',
              keyword,
            };
          }) : [];
        }""",
        keyword,
    )


def dismiss_login_popup(page) -> None:
    try:
        page.evaluate(
            """() => {
              document.querySelectorAll('.login-container').forEach(el => el.remove());
              document.querySelectorAll('.mask, .overlay, [class*="mask"], [class*="overlay"]').forEach(el => {
                if (el.style && (el.style.position === 'fixed' || el.style.position === 'absolute')) el.remove();
              });
              document.body.style.overflow = '';
              document.documentElement.style.overflow = '';
            }"""
        )
    except Exception:
        pass


def collect_search_posts() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    records: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".xiaohongshu" / "browser-data"),
            headless=True,
            proxy={"server": PROXY},
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)

        for index, keyword in enumerate(KEYWORDS, start=1):
            if len(records) >= TARGET * 2 and index > 30:
                break
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed"
            print(f"[{index}/{len(KEYWORDS)}] {keyword}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(5500, 8000))
                dismiss_login_popup(page)

                last_count = 0
                stable_rounds = 0
                for _ in range(18):
                    items = extract_items_from_state(page, keyword)
                    for item in items:
                        note_id = str(item.get("id") or "").strip()
                        if not note_id or "#" in note_id:
                            continue
                        published_at = note_time(note_id)
                        if not published_at or published_at < START_AT or published_at > NOW:
                            continue
                        title = str(item.get("title") or "").strip()
                        desc = str(item.get("desc") or "").strip()
                        author = str(item.get("author") or "").strip()
                        token = str(item.get("xsec_token") or "").strip()
                        if not title or not author:
                            continue
                        score = relevance_score(title, desc, keyword)
                        if score < 0:
                            continue
                        existing = records.get(note_id)
                        if existing:
                            if keyword not in existing["matched_keywords"]:
                                existing["matched_keywords"].append(keyword)
                            existing["relevance_score"] = max(existing["relevance_score"], score)
                            if token and "xsec_token=" not in existing["帖子链接"]:
                                existing["帖子链接"] = make_url(note_id, token)
                            continue
                        records[note_id] = {
                            "note_id": note_id,
                            "帖子标题": title,
                            "帖子链接": make_url(note_id, token),
                            "点赞": to_int(item.get("liked_count")),
                            "评论": to_int(item.get("comment_count")),
                            "收藏": to_int(item.get("collected_count")),
                            "shared_count": to_int(item.get("shared_count")),
                            "author": author,
                            "author_id": str(item.get("author_id") or "").strip(),
                            "author_xsec_token": str(item.get("author_xsec_token") or "").strip(),
                            "published_at": published_at.isoformat(),
                            "desc": desc,
                            "matched_keywords": [keyword],
                            "relevance_score": score,
                        }

                    if len(records) == last_count:
                        stable_rounds += 1
                    else:
                        stable_rounds = 0
                    last_count = len(records)
                    if len(records) >= TARGET and stable_rounds >= 2:
                        break
                    page.mouse.wheel(0, random.randint(1600, 2600))
                    page.wait_for_timeout(random.randint(1100, 1800))

                raw = {
                    "keyword": keyword,
                    "collected_total": len(records),
                    "items_seen": len(extract_items_from_state(page, keyword)),
                    "url": page.url,
                }
                (RAW_DIR / f"{index:02d}_{safe_filename(keyword)}.json").write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:
                failures.append({"keyword": keyword, "error": f"{type(exc).__name__}: {exc}"})
                print(f"  error: {exc}", flush=True)
            time.sleep(random.uniform(1.2, 2.4))

        context.close()

    rows = list(records.values())
    rows.sort(key=lambda r: (-r["relevance_score"], -int(r["点赞"]), r["published_at"]))
    return rows[:TARGET], failures


def safe_filename(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value).strip("_")[:80]


def load_profile_cache() -> dict[str, Any]:
    if PROFILE_CACHE.exists():
        try:
            data = json.loads(PROFILE_CACHE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_profile_cache(cache: dict[str, Any]) -> None:
    PROFILE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_profile_from_state(page) -> dict[str, Any] | None:
    return page.evaluate(
        """() => {
          const state = window.__INITIAL_STATE__ || {};
          const result = { texts: [], interactions: [] };
          const seen = new WeakSet();
          function addText(value) {
            if (typeof value !== 'string') return;
            const text = value.trim();
            if (text && result.texts.length < 240) result.texts.push(text.slice(0, 300));
          }
          function addInteraction(item) {
            if (!item || typeof item !== 'object' || result.interactions.length >= 30) return;
            const name = item.name || item.type || item.label || item.title || '';
            const count = item.i18nCount || item.count || item.num || item.value || '';
            if (name || count) result.interactions.push({ name: String(name), count: String(count) });
          }
          function walk(obj, depth) {
            if (!obj || depth > 5) return;
            if (typeof obj === 'string') {
              addText(obj);
              return;
            }
            if (Array.isArray(obj)) {
              for (const v of obj.slice(0, 50)) {
                addInteraction(v);
                walk(v, depth + 1);
              }
              return;
            }
            if (typeof obj === 'object') {
              if (seen.has(obj)) return;
              seen.add(obj);
              if (obj.interactions) walk(obj.interactions, depth + 1);
              for (const [k, v] of Object.entries(obj)) {
                if (typeof v === 'string' && /(desc|description|nick|name|red|location|wechat|wx|phone|email|bio|sign)/i.test(k)) addText(v);
                if (/(user|profile|info|basic|interactions|desc|description)/i.test(k) || depth < 2) walk(v, depth + 1);
              }
            }
          }
          walk(state, 0);
          return (result.texts.length || result.interactions.length) ? result : null;
        }"""
    )


def followers_from_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.replace("|", " "))
    patterns = [
        r"(?<![\d.])(\d+(?:\.\d+)?\s*(?:万|w|W|k|K)?)\s*粉丝",
        r"粉丝\s*(\d+(?:\.\d+)?\s*(?:万|w|W|k|K)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return re.sub(r"\s+", "", match.group(1))
    return ""


def normalize_profile(profile: dict[str, Any] | None, body_text: str = "") -> tuple[str, str]:
    if not profile and not body_text:
        return "获取失败", "获取失败"

    blob = json.dumps(profile or {}, ensure_ascii=False)
    followers = ""
    follower_match = re.search(r'"(?:name|type)"\s*:\s*"(?:粉丝|fans)"[^{}]{0,160}?"(?:i18nCount|count)"\s*:\s*"?([^",}]+)', blob)
    if not follower_match:
        follower_match = re.search(r'"(?:i18nCount|count)"\s*:\s*"?([^",}]+)"?[^{}]{0,120}"(?:name|type)"\s*:\s*"(?:粉丝|fans)"', blob)
    if follower_match:
        followers = follower_match.group(1)
    if not followers:
        followers = followers_from_text(body_text)

    texts: list[str] = []
    def collect_text(obj: Any, depth: int = 0) -> None:
        if depth > 5 or len(texts) > 200:
            return
        if isinstance(obj, str):
            if obj.strip():
                texts.append(obj.strip())
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in {"desc", "description", "nickname", "redid", "red_id", "ip_location"} or isinstance(value, (dict, list)):
                    collect_text(value, depth + 1)
        elif isinstance(obj, list):
            for value in obj[:50]:
                collect_text(value, depth + 1)

    collect_text(profile)
    contact = contact_from_text(" ".join([body_text, *texts]))
    return followers or "未显示", contact


def contact_from_text(text: str) -> str:
    cleaned_lines = []
    for line in str(text).splitlines():
        if "小红书号" in line:
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    found: list[str] = []
    for label, pattern in CONTACT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            value = value.strip(" ：:，,。.;；")
            item = f"{label}: {value}"
            if value and item not in found:
                found.append(item)
    return "；".join(found) if found else "未发现"


def profile_header_text(body_text: str) -> str:
    text = str(body_text or "")
    marker = "电话：9501-3888"
    index = text.rfind(marker)
    if index >= 0:
        text = text[index + len(marker):]
    for stop in ["\n关注\n笔记", "\n笔记\n收藏", "\nTA 还没有收藏"]:
        stop_index = text.find(stop)
        if stop_index > 0:
            text = text[:stop_index]
            break
    return text


def profile_record_has_public_data(record: dict[str, Any]) -> bool:
    if not record:
        return False
    if record.get("status") == "ok":
        return True
    body_text = str(record.get("body_text") or "")
    if "请求太频繁" in body_text or "扫码验证身份" in body_text or "保护账号安全" in body_text:
        return False
    return bool(followers_from_text(body_text) or contact_from_text(profile_header_text(body_text)) != "未发现")


def enrich_profiles(rows: list[dict[str, Any]]) -> None:
    cache = load_profile_cache()
    author_ids = []
    author_tokens: dict[str, str] = {}
    for row in rows:
        author_id = row.get("author_id", "")
        if author_id and author_id not in author_ids:
            author_ids.append(author_id)
        if author_id and row.get("author_xsec_token") and author_id not in author_tokens:
            author_tokens[author_id] = str(row.get("author_xsec_token") or "")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".xiaohongshu" / "browser-data"),
            headless=True,
            proxy={"server": PROXY},
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled", "--disable-features=AutomationControlled", "--no-sandbox"],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)

        for index, author_id in enumerate(author_ids, start=1):
            if profile_record_has_public_data(cache.get(author_id, {})):
                continue
            print(f"profile [{index}/{len(author_ids)}] {author_id}", flush=True)
            try:
                page.goto(profile_home_url(author_id, author_tokens.get(author_id, "")), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4200, 6500))
                dismiss_login_popup(page)
                body_text = page.evaluate("() => document.body.innerText.slice(0, 5000)")
                verify_required = "扫码验证身份" in body_text or "保护账号安全" in body_text
                profile = None if verify_required else parse_profile_from_state(page)
                cache[author_id] = {
                    "status": "verify_required" if verify_required else ("ok" if profile or "粉丝" in body_text else "no_state"),
                    "profile": profile,
                    "body_text": body_text,
                    "fetched_at": datetime.now(TZ).isoformat(),
                }
            except Exception as exc:
                cache[author_id] = {
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "profile": None,
                    "body_text": "",
                    "fetched_at": datetime.now(TZ).isoformat(),
                }
            save_profile_cache(cache)
            if index % 10 == 0:
                time.sleep(random.uniform(22.0, 36.0))
            else:
                time.sleep(random.uniform(8.0, 13.0))
        context.close()

    for row in rows:
        author_id = row.get("author_id", "")
        profile_record = cache.get(author_id, {})
        body_text = profile_record.get("body_text", "")
        followers, contact = normalize_profile(profile_record.get("profile"), body_text)
        row["帖主主页链接"] = profile_home_url(author_id, str(row.get("author_xsec_token") or ""))
        row["粉丝数"] = followers
        row["联系方式"] = contact or "未发现"
        row["建议评论"] = compact_comment(row)
        row["profile_status"] = profile_record.get("status", "missing")


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            0 if r.get("联系方式") and r.get("联系方式") not in {"未发现", "获取失败"} else 1,
            -follower_sort_value(str(r.get("粉丝数") or "")),
            -int(r.get("点赞") or 0),
        ),
    )


def write_outputs(rows: list[dict[str, Any]], failures: list[dict[str, str]]) -> None:
    headers = ["帖子标题", "帖子链接", "点赞", "评论", "收藏", "建议评论", "帖主主页链接", "粉丝数", "联系方式"]
    md_lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---:|---:|---:|---|---|---:|---|",
    ]
    for row in rows:
        md_lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["帖子标题"]),
                    f"[打开]({row['帖子链接']})",
                    str(row["点赞"]),
                    str(row["评论"]),
                    str(row["收藏"]),
                    md_escape(row["建议评论"]),
                    f"[打开]({row['帖主主页链接']})" if row.get("帖主主页链接") else "",
                    md_escape(row.get("粉丝数", "")),
                    md_escape(row.get("联系方式", "")),
                ]
            )
            + " |"
        )

    markdown = "\n".join(md_lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.write_text(markdown, encoding="utf-8")

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})

    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "meta": {
                    "generated_at": datetime.now(TZ).isoformat(),
                    "window_start": START_AT.isoformat(),
                    "window_end": NOW.isoformat(),
                    "target": TARGET,
                    "row_count": len(rows),
                    "keywords": KEYWORDS,
                    "exclude_rule": EXCLUDE_RE.pattern,
                    "sort_rule": "联系方式非空优先；各组内按粉丝数从高到低；同粉丝数按点赞从高到低",
                    "failures": failures,
                },
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    rows, failures = collect_search_posts()
    if len(rows) < TARGET:
        print(f"warning: only {len(rows)} rows after filtering", flush=True)
    enrich_profiles(rows)
    rows = sort_rows(rows[:TARGET])
    write_outputs(rows, failures)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "output_json": str(OUTPUT_JSON),
                "contacts": sum(1 for row in rows if row.get("联系方式") not in {"未发现", "获取失败", ""}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
