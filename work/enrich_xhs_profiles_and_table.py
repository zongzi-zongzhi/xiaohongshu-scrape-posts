from __future__ import annotations

import json
import re
import sys
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
BASE_MD = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_comments_humanized.md"
BASE_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100.json"
PROFILE_CACHE = ROOT / "outputs" / "xhs_insforge_author_profiles_cache.json"
OUTPUT_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_profiles.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_profiles.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书痛点+建议评论方向_含帖主信息.md")

TZ = timezone(timedelta(hours=8))


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def repair_text(value: Any) -> str:
    text = "" if value is None else str(value)
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        return text
    return repaired if cjk_count(repaired) > cjk_count(text) else text


def parse_md_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for ch in line:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            current.append(ch)
            escaped = True
        elif ch == "|":
            cells.append("".join(current).strip().replace(r"\|", "|"))
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip().replace(r"\|", "|"))
    return cells


def parse_md_table(path: Path) -> list[dict[str, str]]:
    lines = [line for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    table_lines = [line for line in lines if line.lstrip().startswith("|")]
    if len(table_lines) < 3:
        raise ValueError(f"No markdown table found: {path}")

    headers = parse_md_row(table_lines[0])
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = parse_md_row(line)
        if len(cells) != len(headers):
            raise ValueError(f"Expected {len(headers)} cells, got {len(cells)}: {line[:160]}")
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def extract_url(markdown_link: str) -> str:
    match = re.search(r"\[[^\]]+\]\((.*?)\)", markdown_link)
    return match.group(1) if match else markdown_link.strip()


def note_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def md_escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")


def load_posts_by_note_id() -> dict[str, dict[str, Any]]:
    data = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    return {post["note_id"]: post for post in data["posts"]}


def load_cache() -> dict[str, dict[str, Any]]:
    if not PROFILE_CACHE.exists():
        return {}
    try:
        data = json.loads(PROFILE_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(cache: dict[str, dict[str, Any]]) -> None:
    PROFILE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def followers_from_profile(profile: dict[str, Any]) -> str:
    interactions = profile.get("interactions") or []
    for item in interactions:
        if item.get("type") == "fans":
            return repair_text(item.get("i18nCount") or item.get("count") or "")
    for item in interactions:
        name = repair_text(item.get("name") or "")
        if "粉丝" in name:
            return repair_text(item.get("i18nCount") or item.get("count") or "")
    return ""


CONTACT_PATTERNS = [
    ("邮箱", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)),
    ("手机号", re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")),
    ("微信", re.compile(r"(?:微信|VX|vx|V信|v信|WeChat|wechat|wx|WX|加V|加v)[号：:\s]*([A-Za-z][A-Za-z0-9_-]{4,19})")),
    ("QQ", re.compile(r"(?:QQ|qq)[号：:\s]*([1-9]\d{4,11})")),
    ("公众号", re.compile(r"(?:公众号|公号|订阅号)[：:\s]*([^，。；;、\s]{2,30})")),
]


def contact_from_profile(profile: dict[str, Any]) -> str:
    basic = profile.get("userBasicInfo") or {}
    fields = [
        repair_text(basic.get("desc") or ""),
        repair_text(basic.get("nickname") or ""),
    ]
    text = " ".join(part for part in fields if part).strip()
    found: list[str] = []
    for label, pattern in CONTACT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            value = value.strip(" ：:，,。.;；")
            item = f"{label}: {value}"
            if value and item not in found:
                found.append(item)
    return "；".join(found) if found else "未发现"


def profile_home_url(author_id: str) -> str:
    return f"https://www.xiaohongshu.com/user/profile/{author_id}" if author_id else ""


def ensure_profiles(author_ids: list[str], cache: dict[str, dict[str, Any]]) -> None:
    pending = [
        author_id
        for author_id in author_ids
        if author_id and cache.get(author_id, {}).get("status") != "ok"
    ]
    if not pending:
        return

    sys.path.insert(0, str(SKILL_DIR))
    from scripts.client import CaptchaError, XiaohongshuClient
    from scripts.user import UserProfileAction

    client = XiaohongshuClient(headless=True)
    client.start()
    try:
        action = UserProfileAction(client)
        for index, author_id in enumerate(pending, start=1):
            print(f"[{index}/{len(pending)}] profile {author_id}", flush=True)
            try:
                profile = action.get_user_profile(author_id)
                if profile:
                    cache[author_id] = {
                        "status": "ok",
                        "profile": profile,
                        "fetched_at": datetime.now(TZ).isoformat(),
                    }
                else:
                    cache[author_id] = {
                        "status": "no_data",
                        "profile": None,
                        "fetched_at": datetime.now(TZ).isoformat(),
                    }
            except CaptchaError as exc:
                cache.pop(author_id, None)
                save_cache(cache)
                print(
                    json.dumps(
                        {
                            "status": "captcha",
                            "author_id": author_id,
                            "message": str(exc),
                            "hint": "请用可见浏览器完成验证后重试，脚本会从缓存继续。",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                raise SystemExit(2) from exc
            except Exception as exc:
                cache[author_id] = {
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "profile": None,
                    "fetched_at": datetime.now(TZ).isoformat(),
                }
                print(f"error {author_id}: {exc}", file=sys.stderr, flush=True)
            save_cache(cache)
            time.sleep(random.uniform(8.0, 13.0))
    finally:
        client.close()


def build_rows() -> list[dict[str, Any]]:
    md_rows = parse_md_table(BASE_MD)
    posts_by_note_id = load_posts_by_note_id()
    cache = load_cache()

    author_ids: list[str] = []
    for row in md_rows:
        note_id = note_id_from_url(extract_url(row["帖子链接"]))
        post = posts_by_note_id.get(note_id, {})
        author_id = str(post.get("author_id") or "").strip()
        if author_id and author_id not in author_ids:
            author_ids.append(author_id)

    ensure_profiles(author_ids, cache)

    enriched: list[dict[str, Any]] = []
    for row in md_rows:
        url = extract_url(row["帖子链接"])
        note_id = note_id_from_url(url)
        post = posts_by_note_id.get(note_id, {})
        author_id = str(post.get("author_id") or "").strip()
        cached = cache.get(author_id, {})
        profile = cached.get("profile") if cached.get("status") == "ok" else None
        followers = followers_from_profile(profile or {}) if profile else "获取失败"
        contact = contact_from_profile(profile or {}) if profile else "获取失败"
        enriched.append(
            {
                "帖子标题": row["帖子标题"],
                "帖子链接": url,
                "点赞": row["点赞"],
                "评论": row["评论"],
                "收藏": row["收藏"],
                "建议评论": row.get("建议评论") or row.get("建议评论方向") or "",
                "帖主主页链接": profile_home_url(author_id),
                "粉丝数": followers or "未显示",
                "联系方式": contact,
                "author": post.get("author", ""),
                "author_id": author_id,
                "note_id": note_id,
                "profile_status": cached.get("status", "missing"),
            }
        )
    return enriched


def write_markdown(rows: list[dict[str, Any]]) -> None:
    headers = ["帖子标题", "帖子链接", "点赞", "评论", "收藏", "建议评论", "帖主主页链接", "粉丝数", "联系方式"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---:|---:|---:|---|---|---:|---|",
    ]
    for row in rows:
        cells = []
        for header in headers:
            if header == "帖子链接":
                cells.append(f"[打开]({row[header]})")
            elif header == "帖主主页链接" and row[header]:
                cells.append(f"[打开]({row[header]})")
            else:
                cells.append(md_escape(row[header]))
        lines.append("| " + " | ".join(cells) + " |")

    markdown = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.write_text(markdown, encoding="utf-8")


def main() -> None:
    rows = build_rows()
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "meta": {
                    "generated_at": datetime.now(TZ).isoformat(),
                    "source_md": str(BASE_MD),
                    "source_json": str(BASE_JSON),
                    "profile_cache": str(PROFILE_CACHE),
                    "row_count": len(rows),
                },
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_markdown(rows)
    ok_profiles = sum(1 for row in rows if row["profile_status"] == "ok")
    print(json.dumps({"rows": len(rows), "profiles_ok_rows": ok_profiles, "output_md": str(OUTPUT_MD), "inbox_md": str(INBOX_MD)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
