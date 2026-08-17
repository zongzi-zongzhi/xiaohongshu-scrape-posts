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


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
CANDIDATE_JSON = OUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.json"
OUTPUT_JSON = OUT_DIR / "xhs_insforge_since_20260723_title_body.json"
OUTPUT_MD = OUT_DIR / "xhs_insforge_since_20260723_title_body.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书痛点帖子正文_新增_20260723-20260726.md")
TZ = timezone(timedelta(hours=8))


def md_escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")


def normalize_body(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", str(text or ""))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def body_from_visible_text(text: str, title: str) -> str:
    text = str(text or "")
    if not text:
        return ""
    start = text.find(title) if title else -1
    if start >= 0:
        text = text[start + len(title):]
    elif title:
        return ""
    stop_markers = [
        "\n共 ",
        "\n评论",
        "\n说点什么",
        "\n相关推荐",
        "\n分享",
        "\n赞",
        "\n收藏",
    ]
    stop_positions = [text.find(marker) for marker in stop_markers if text.find(marker) > 0]
    if stop_positions:
        text = text[: min(stop_positions)]
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in {"首页", "点点", "ai", "RED", "直播", "发布", "通知", "消息", "我", "打开看看", "登录"}:
            continue
        if "沪ICP备" in line or "行吟信息科技" in line or "违法不良信息" in line:
            continue
        lines.append(line)
    return normalize_body("\n".join(lines))


def extract_detail(page, row: dict[str, Any]) -> dict[str, str]:
    note_id = row.get("note_id", "")
    title = row.get("帖子标题", "")
    state = page.evaluate(
        """(noteId) => {
          const detailMapRef = window.__INITIAL_STATE__?.note?.noteDetailMap;
          const detailMap = detailMapRef?.value || detailMapRef?._value || detailMapRef || {};
          const direct = detailMap?.[noteId] || null;
          function unwrap(obj) {
            if (!obj || typeof obj !== 'object') return {};
            const note = obj.note || obj.noteDetail?.note || obj.noteData || obj.noteCard || obj;
            const card = note.noteCard || note;
            return {
              title: note.title || note.displayTitle || card.displayTitle || card.title || '',
              desc: note.desc || note.description || note.content || card.desc || card.description || '',
            };
          }
          return unwrap(direct);
        }""",
        note_id,
    )
    state_title = normalize_body(state.get("title") or "")
    state_body = normalize_body(state.get("desc") or "")
    if state_body:
        return {"title": state_title or title, "body": state_body, "source": "detail_state"}

    body_text = page.evaluate("() => document.body.innerText.slice(0, 8000)")
    visible_body = body_from_visible_text(body_text, state_title or title)
    if visible_body:
        return {"title": state_title or title, "body": visible_body, "source": "visible_text"}

    return {
        "title": state_title or title,
        "body": normalize_body(row.get("desc") or ""),
        "source": "search_desc",
    }


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    headers = ["帖子链接", "帖子名字", "帖子正文部分"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[打开]({row['帖子链接']})",
                    md_escape(row["帖子名字"]),
                    md_escape(row["帖子正文部分"]),
                ]
            )
            + " |"
        )
    markdown = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.write_text(markdown, encoding="utf-8")
    OUTPUT_JSON.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing_candidates() -> list[dict[str, Any]]:
    if not CANDIDATE_JSON.exists():
        return []
    try:
        data = json.loads(CANDIDATE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in data.get("rows", []):
        note_id = str(row.get("note_id") or "").strip()
        if not note_id or note_id in seen:
            continue
        published_at = base.note_time(note_id)
        if not published_at or published_at < base.START_AT or published_at > base.NOW:
            continue
        title = str(row.get("帖子标题") or "").strip()
        desc = str(row.get("desc") or "").strip()
        keyword_text = " ".join(row.get("matched_keywords") or [])
        if base.relevance_score(title, desc, keyword_text) < 0:
            continue
        copied = dict(row)
        copied["published_at"] = row.get("published_at") or published_at.isoformat()
        rows.append(copied)
        seen.add(note_id)

    rows.sort(key=lambda row: (row.get("published_at") or ""), reverse=True)
    return rows[: base.TARGET]


def main() -> None:
    failures: list[dict[str, str]] = []
    search_rows = load_existing_candidates()
    if search_rows:
        print(f"loaded {len(search_rows)} existing candidates in window", flush=True)
    else:
        search_rows, failures = base.collect_search_posts()
    selected = search_rows[: base.TARGET]
    print(f"selected {len(selected)} rows in window", flush=True)

    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "window_start": base.START_AT.isoformat(),
        "window_end": base.NOW.isoformat(),
        "keywords": base.KEYWORDS,
        "row_count": 0,
        "failures": failures,
        "note": "严格保留时间窗内 AI Coding / 后端 / 数据库 / Supabase / 部署 / 安全相关帖子；最多 100 条，不硬凑。",
    }
    rows: list[dict[str, Any]] = []
    write_outputs(rows, meta)

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

        for index, row in enumerate(selected, start=1):
            print(f"detail [{index}/{len(selected)}] {row['note_id']} {row['帖子标题']}", flush=True)
            body = normalize_body(row.get("desc") or "")
            detail_source = "search_desc"
            title = row["帖子标题"]
            try:
                page.goto(row["帖子链接"], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(random.randint(4500, 7000))
                base.dismiss_login_popup(page)
                page.wait_for_timeout(random.randint(1200, 2200))
                visible = page.evaluate("() => document.body.innerText.slice(0, 1000)")
                if "扫码验证身份" in visible or "保护账号安全" in visible:
                    body = body or "（详情页触发安全验证，正文未完整获取）"
                    detail_source = "verify_required"
                elif "请求太频繁" in visible:
                    body = body or "（详情页请求太频繁，正文未完整获取）"
                    detail_source = "too_frequent"
                else:
                    detail = extract_detail(page, row)
                    title = detail["title"] or title
                    body = detail["body"] or body
                    detail_source = detail["source"]
            except Exception as exc:
                body = body or f"（详情页获取失败：{type(exc).__name__}）"
                detail_source = "error"

            rows.append(
                {
                    "帖子链接": row["帖子链接"],
                    "帖子名字": title,
                    "帖子正文部分": body or "（未获取到正文）",
                    "note_id": row["note_id"],
                    "published_at": row.get("published_at"),
                    "detail_source": detail_source,
                }
            )
            meta["row_count"] = len(rows)
            write_outputs(rows, meta)
            if index % 12 == 0:
                time.sleep(random.uniform(18.0, 30.0))
            else:
                time.sleep(random.uniform(3.0, 6.0))
        context.close()

    meta["completed_at"] = datetime.now(TZ).isoformat()
    meta["row_count"] = len(rows)
    write_outputs(rows, meta)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "output_json": str(OUTPUT_JSON),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
