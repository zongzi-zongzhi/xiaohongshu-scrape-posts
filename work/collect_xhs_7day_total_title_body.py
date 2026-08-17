from __future__ import annotations

import json
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

import collect_xhs_since_last_crawl as base
from collect_xhs_since_title_body import extract_detail, md_escape, normalize_body


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
INBOX = Path(r"D:\czj note\00_Inbox")

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
TODAY_START = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
YESTERDAY_START = TODAY_START - timedelta(days=1)
SEVEN_DAY_START = TODAY_START - timedelta(days=6)

OUTPUT_JSON = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.json"
OUTPUT_MD = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.md"
NEW_ONLY_JSON = OUT_DIR / "xhs_insforge_title_body_new_20260726_20260727.json"
INBOX_MD = INBOX / "小红书痛点帖子正文_7天总和版_20260721-20260727.md"
INBOX_NEW_MD = INBOX / "小红书痛点帖子正文_新增_20260726-20260727.md"

HIST_BODY_FILES = [
    OUT_DIR / "xhs_insforge_since_20260723_title_body_filtered.json",
]
HIST_POST_FILES = [
    OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100.json",
    OUT_DIR / "xhs_insforge_pain_posts_100_recent.json",
]

EXCLUDE_RE = re.compile(
    r"(实习|实习生|招聘|招人|招募|招生|内推|校招|社招|秋招|春招|求职|简历|面试|产品岗|岗位|"
    r"找工作|上岸|薪资|工资|应届|跳槽|外包|路演|大会|线下|直播|专场|公开课|体验课|报名|学员|"
    r"宝藏网站|工具合集|工具推荐|视频项目|按场景选工具|选题荒|内容创作|一周内容|提示词|"
    r"个人成长|市场情绪|自由职业|副业|搞钱|不想上班)"
)
INCLUDE_RE = re.compile(
    r"(踩坑|避坑|翻车|卡住|报错|小白|新手|零基础|后端|数据库|Supabase|supabase|RLS|rls|"
    r"API|api|密钥|Key|key|登录|鉴权|权限|部署|上线|MVP|mvp|项目|产品|AI APP|CRM|"
    r"AI Agent|Agent|MCP|mcp|vibecoding|Vibe Coding|AI Coding|Cursor|Codex)"
)


def published_from_note_id(note_id: str) -> datetime | None:
    return base.note_time(str(note_id or ""))


def parse_dt(value: Any, fallback_note_id: str = "") -> datetime | None:
    if value:
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(TZ)
        except Exception:
            pass
    return published_from_note_id(fallback_note_id)


def format_dt(value: datetime | str | None) -> str:
    dt = parse_dt(value) if not isinstance(value, datetime) else value
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def note_id_from_url(url: str) -> str:
    match = re.search(r"/explore/([0-9a-f]{24})", str(url or ""))
    return match.group(1) if match else ""


def make_url(note_id: str, token: str = "") -> str:
    if not note_id:
        return ""
    return base.make_url(note_id, token)


def normalize_candidate(raw: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    note_id = str(raw.get("note_id") or raw.get("id") or note_id_from_url(raw.get("帖子链接") or raw.get("url") or "")).strip()
    if not note_id:
        return None
    published_at = parse_dt(raw.get("published_at"), note_id)
    if not published_at or published_at < SEVEN_DAY_START or published_at > NOW:
        return None

    title = str(raw.get("帖子名字") or raw.get("帖子标题") or raw.get("title") or "").strip()
    body = normalize_body(raw.get("帖子正文部分") or raw.get("desc") or raw.get("description") or "")
    url = str(raw.get("帖子链接") or raw.get("url") or "").strip()
    if not url:
        url = make_url(note_id, str(raw.get("xsec_token") or raw.get("xsecToken") or ""))
    if not title or not url:
        return None

    matched = raw.get("matched_keywords") or raw.get("matched_keywords_text") or raw.get("keyword") or ""
    if isinstance(matched, list):
        matched_text = " ".join(str(item) for item in matched)
    else:
        matched_text = str(matched)

    return {
        "note_id": note_id,
        "published_at": published_at.isoformat(),
        "帖子链接": url,
        "帖子名字": title,
        "帖子正文部分": body,
        "source": source,
        "matched_keywords": matched_text,
        "detail_source": raw.get("detail_source") or ("existing_body" if body else "pending"),
    }


def final_keep(row: dict[str, Any]) -> bool:
    text = f"{row.get('帖子名字', '')}\n{row.get('帖子正文部分', '')}"
    if EXCLUDE_RE.search(text):
        return False
    return bool(INCLUDE_RE.search(text))


def add_candidate(candidates: dict[str, dict[str, Any]], candidate: dict[str, Any] | None) -> None:
    if not candidate:
        return
    note_id = candidate["note_id"]
    existing = candidates.get(note_id)
    if not existing:
        candidates[note_id] = candidate
        return
    if not existing.get("帖子正文部分") and candidate.get("帖子正文部分"):
        existing.update(candidate)
    elif candidate.get("source") == "new_search" and existing.get("source") != "new_search":
        existing["source"] = f"{existing.get('source')},new_search"


def load_historical_candidates() -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    for path in HIST_BODY_FILES:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("rows", []):
            add_candidate(candidates, normalize_candidate(raw, source=path.name))

    for path in HIST_POST_FILES:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("posts", []):
            candidate = normalize_candidate(raw, source=path.name)
            if not candidate:
                continue
            published_at = parse_dt(candidate["published_at"])
            if not published_at or published_at >= YESTERDAY_START:
                continue
            # Older JSON has no body. Keep likely pain candidates so details can be fetched.
            title_keywords = f"{candidate['帖子名字']} {candidate.get('matched_keywords', '')}"
            if not INCLUDE_RE.search(title_keywords) or EXCLUDE_RE.search(title_keywords):
                continue
            add_candidate(candidates, candidate)

    return candidates


def extract_items_from_search(page, keyword: str) -> list[dict[str, Any]]:
    return page.evaluate(
        """(keyword) => {
          const feeds = window.__INITIAL_STATE__?.search?.feeds;
          const arr = feeds?.value || feeds?._value || [];
          return Array.isArray(arr) ? arr.map((item) => {
            const nc = item.noteCard || item.note_card || {};
            const info = nc.interactInfo || nc.interact_info || {};
            return {
              note_id: item.id || nc.noteId || nc.note_id || '',
              xsec_token: item.xsecToken || item.xsec_token || '',
              title: nc.displayTitle || nc.title || '',
              desc: nc.desc || '',
              liked_count: info.likedCount || info.liked_count || '0',
              comment_count: info.commentCount || info.comment_count || '0',
              collected_count: info.collectedCount || info.collected_count || '0',
              keyword,
            };
          }) : [];
        }""",
        keyword,
    )


def search_new_window() -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".xiaohongshu" / "browser-data"),
            headless=True,
            proxy={"server": base.PROXY},
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled", "--disable-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        for index, keyword in enumerate(base.KEYWORDS, start=1):
            print(f"search [{index}/{len(base.KEYWORDS)}] {keyword}", flush=True)
            try:
                page.goto(f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4500, 7000))
                base.dismiss_login_popup(page)
                stable = 0
                last_count = len(rows)
                for _ in range(12):
                    for item in extract_items_from_search(page, keyword):
                        note_id = str(item.get("note_id") or "").strip()
                        published_at = published_from_note_id(note_id)
                        if not published_at or published_at < YESTERDAY_START or published_at > NOW:
                            continue
                        title = str(item.get("title") or "").strip()
                        desc = str(item.get("desc") or "").strip()
                        if not title or base.relevance_score(title, desc, keyword) < 0:
                            continue
                        existing = rows.get(note_id)
                        if existing:
                            existing["matched_keywords"] += f" {keyword}"
                            continue
                        rows[note_id] = {
                            "note_id": note_id,
                            "published_at": published_at.isoformat(),
                            "title": title,
                            "desc": desc,
                            "url": make_url(note_id, str(item.get("xsec_token") or "")),
                            "keyword": keyword,
                            "matched_keywords": keyword,
                        }
                    if len(rows) == last_count:
                        stable += 1
                    else:
                        stable = 0
                    last_count = len(rows)
                    if stable >= 2:
                        break
                    page.mouse.wheel(0, random.randint(1500, 2400))
                    page.wait_for_timeout(random.randint(900, 1600))
            except Exception as exc:
                print(f"search error {keyword}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            time.sleep(random.uniform(1.0, 2.0))
        context.close()

    result = []
    for raw in rows.values():
        candidate = normalize_candidate(raw, source="new_search")
        if candidate:
            result.append(candidate)
    result.sort(key=lambda row: row["published_at"], reverse=True)
    return result


def fetch_missing_bodies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending = [row for row in rows if not row.get("帖子正文部分")]
    if not pending:
        return rows
    print(f"detail pending {len(pending)}", flush=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".xiaohongshu" / "browser-data"),
            headless=True,
            proxy={"server": base.PROXY},
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled", "--disable-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        for index, row in enumerate(pending, start=1):
            print(f"detail [{index}/{len(pending)}] {row['note_id']} {row['帖子名字']}", flush=True)
            try:
                page.goto(row["帖子链接"], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4500, 7000))
                base.dismiss_login_popup(page)
                visible = page.evaluate("() => document.body.innerText.slice(0, 1200)")
                if "扫码验证身份" in visible or "保护账号安全" in visible:
                    row["帖子正文部分"] = row.get("帖子正文部分") or "（详情页触发安全验证，正文未完整获取）"
                    row["detail_source"] = "verify_required"
                elif "请求太频繁" in visible:
                    row["帖子正文部分"] = row.get("帖子正文部分") or "（详情页请求太频繁，正文未完整获取）"
                    row["detail_source"] = "too_frequent"
                else:
                    detail = extract_detail(page, {"note_id": row["note_id"], "帖子标题": row["帖子名字"], "desc": row.get("帖子正文部分", "")})
                    row["帖子名字"] = detail["title"] or row["帖子名字"]
                    row["帖子正文部分"] = detail["body"] or row.get("帖子正文部分") or "（未获取到正文）"
                    row["detail_source"] = detail["source"]
            except Exception as exc:
                row["帖子正文部分"] = row.get("帖子正文部分") or f"（详情页获取失败：{type(exc).__name__}）"
                row["detail_source"] = "error"
            if index % 12 == 0:
                time.sleep(random.uniform(18.0, 30.0))
            else:
                time.sleep(random.uniform(3.0, 6.0))
        context.close()
    return rows


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "| 发布时间 | 帖子链接 | 帖子名字 | 帖子正文部分 |",
        "|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    format_dt(row.get("published_at")),
                    f"[打开]({row['帖子链接']})",
                    md_escape(row["帖子名字"]),
                    md_escape(row["帖子正文部分"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    candidates = load_historical_candidates()
    print(f"loaded historical candidates {len(candidates)}", flush=True)
    new_rows = search_new_window()
    print(f"new window candidates {len(new_rows)}", flush=True)
    for row in new_rows:
        add_candidate(candidates, row)

    rows = list(candidates.values())
    rows = fetch_missing_bodies(rows)
    rows = [row for row in rows if final_keep(row)]
    rows.sort(key=lambda row: parse_dt(row.get("published_at")) or SEVEN_DAY_START, reverse=True)

    new_only = [row for row in rows if (parse_dt(row.get("published_at")) or SEVEN_DAY_START) >= YESTERDAY_START]
    write_markdown(OUTPUT_MD, rows)
    write_markdown(INBOX_MD, rows)
    write_markdown(INBOX_NEW_MD, new_only)

    payload = {
        "meta": {
            "generated_at": datetime.now(TZ).isoformat(),
            "seven_day_start": SEVEN_DAY_START.isoformat(),
            "new_window_start": YESTERDAY_START.isoformat(),
            "window_end": NOW.isoformat(),
            "row_count": len(rows),
            "new_window_row_count": len(new_only),
            "sort_rule": "published_at desc",
            "columns": ["发布时间", "帖子链接", "帖子名字", "帖子正文部分"],
        },
        "rows": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    NEW_ONLY_JSON.write_text(json.dumps({"meta": payload["meta"], "rows": new_only}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "new_window_rows": len(new_only),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "new_inbox_md": str(INBOX_NEW_MD),
                "output_json": str(OUTPUT_JSON),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
