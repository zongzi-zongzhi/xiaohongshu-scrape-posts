from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
XHS_SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
SOURCE_JSON = ROOT / "outputs" / "xhs_insforge_expanded_leads_comments_7day_no_profile_20260721_20260727.json"
OUTPUT_JSON = ROOT / "outputs" / "xhs_insforge_minimal_full_body_20260721_20260727.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_minimal_full_body_20260721_20260727.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书建联线索池_精简列_正文补全_20260721-20260727.md")
LARK_FIELDS_JSON = ROOT / "work" / "xhs_minimal_full_body_base_fields.json"
LARK_RECORDS_JSON = ROOT / "work" / "xhs_minimal_full_body_records_payload.json"
LIVE_CACHE_JSON = ROOT / "work" / "xhs_minimal_full_body_live_cache.json"

KEEP_FIELDS = ["发布时间", "帖子名字", "帖子链接", "匹配关键词", "评论例子", "帖子正文部分"]


def note_id_from_url(url: str) -> str:
    match = re.search(r"/explore/([0-9a-f]{24})", str(url or ""))
    return match.group(1) if match else ""


def xsec_token_from_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    values = parse_qs(parsed.query).get("xsec_token", [])
    return values[0] if values else ""


def normalize_body(text: Any) -> str:
    value = str(text or "")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def maybe_fix_mojibake(text: Any) -> str:
    value = str(text or "")
    if not value:
        return ""
    # Some XHS script output can arrive as UTF-8 bytes decoded as latin-1.
    if any(token in value for token in ("å", "æ", "ç", "è", "é", "ã", "ï¼")):
        try:
            fixed = value.encode("latin1").decode("utf-8")
            if sum("\u4e00" <= char <= "\u9fff" for char in fixed) > sum("\u4e00" <= char <= "\u9fff" for char in value):
                return fixed
        except Exception:
            pass
    return value


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def iter_dict_rows(obj: Any):
    if isinstance(obj, dict):
        if all(key in obj for key in ("帖子链接", "帖子正文部分")):
            yield obj
        fields = obj.get("fields")
        rows = obj.get("rows")
        if isinstance(fields, list) and isinstance(rows, list) and "帖子正文部分" in fields:
            for row in rows:
                if isinstance(row, list):
                    yield {field: row[index] if index < len(row) else "" for index, field in enumerate(fields)}
        for key in ("rows", "posts", "candidates", "items", "data", "records"):
            value = obj.get(key)
            if isinstance(value, list):
                for item in value:
                    yield from iter_dict_rows(item)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dict_rows(item)


def row_body(row: dict[str, Any]) -> str:
    return normalize_body(
        row.get("帖子正文部分")
        or row.get("body")
        or row.get("正文")
        or row.get("desc")
        or row.get("description")
        or row.get("content")
        or ""
    )


def row_url(row: dict[str, Any]) -> str:
    return str(row.get("帖子链接") or row.get("url") or row.get("link") or "").strip()


def build_local_body_map() -> dict[str, tuple[str, str]]:
    body_by_id: dict[str, tuple[str, str]] = {}
    for folder in (ROOT / "outputs", ROOT / "work"):
        for path in folder.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for row in iter_dict_rows(data):
                body = row_body(row)
                url = row_url(row)
                note_id = str(row.get("note_id") or row.get("id") or note_id_from_url(url)).strip()
                if not note_id or not body:
                    continue
                if note_id not in body_by_id or len(body) > len(body_by_id[note_id][0]):
                    body_by_id[note_id] = (body, path.name)
    return body_by_id


def note_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    note = detail.get("note")
    if isinstance(note, dict):
        return note
    note_detail = detail.get("noteDetail") or detail.get("note_detail")
    if isinstance(note_detail, dict):
        note = note_detail.get("note")
        if isinstance(note, dict):
            return note
    note_card = detail.get("noteCard") or detail.get("note_card")
    if isinstance(note_card, dict):
        return note_card
    return detail


def fetch_live_bodies(rows: list[dict[str, Any]], *, limit: int | None = None) -> dict[str, dict[str, str]]:
    sys.path.insert(0, str(XHS_SKILL_DIR))
    from scripts.client import CaptchaError, XiaohongshuClient
    from scripts.feed import FeedDetailAction

    missing = [row for row in rows if not row.get("帖子正文部分")]
    if limit is not None:
        missing = missing[:limit]

    results: dict[str, dict[str, str]] = {}
    client = XiaohongshuClient(headless=True)
    try:
        client.start()
        action = FeedDetailAction(client)
        for index, row in enumerate(missing, start=1):
            note_id = note_id_from_url(row["帖子链接"])
            token = xsec_token_from_url(row["帖子链接"])
            print(f"live_detail [{index}/{len(missing)}] {note_id} {row['帖子名字']}", flush=True)
            try:
                detail = action.get_feed_detail(note_id, token, xsec_source="pc_search")
                if not detail:
                    results[note_id] = {"body": "", "title": "", "source": "live_empty"}
                else:
                    note = note_from_detail(detail)
                    body = normalize_body(maybe_fix_mojibake(note.get("desc") or note.get("description") or note.get("content") or ""))
                    title = normalize_body(maybe_fix_mojibake(note.get("title") or note.get("displayTitle") or note.get("display_title") or ""))
                    results[note_id] = {"body": body, "title": title, "source": "live_detail"}
            except CaptchaError as exc:
                state = {
                    "status": "verify_required",
                    "captcha_url": exc.captcha_url,
                    "note_id": note_id,
                    "title": row["帖子名字"],
                    "processed_live": len(results),
                    "remaining_live": len(missing) - index + 1,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                (ROOT / "work" / "xhs_minimal_full_body_verify_required.json").write_text(
                    json.dumps(state, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(json.dumps(state, ensure_ascii=False), flush=True)
                break
            except Exception as exc:
                results[note_id] = {"body": "", "title": "", "source": f"live_error:{type(exc).__name__}"}
                print(f"live_detail_error {note_id} {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            LIVE_CACHE_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(1.0)
    finally:
        client.close()
    LIVE_CACHE_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    data = {"meta": meta, "rows": rows}
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 小红书建联线索池（精简列，正文补全）", ""]
    lines.append("| " + " | ".join(KEEP_FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(KEEP_FIELDS)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(markdown_escape(row.get(field, "")) for field in KEEP_FIELDS) + " |")
    markdown = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(markdown, encoding="utf-8")

    LARK_FIELDS_JSON.write_text(
        json.dumps([{"name": field, "type": "text"} for field in KEEP_FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    LARK_RECORDS_JSON.write_text(
        json.dumps({"fields": KEEP_FIELDS, "rows": [[row.get(field, "") for field in KEEP_FIELDS] for row in rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    source_rows = source["rows"]
    rows: list[dict[str, Any]] = []
    for source_row in source_rows:
        row = {field: source_row.get(field, "") for field in KEEP_FIELDS}
        row["帖子正文部分"] = normalize_body(row.get("帖子正文部分", ""))
        rows.append(row)

    local_body_map = build_local_body_map()
    local_filled = 0
    local_sources: dict[str, int] = {}
    for row in rows:
        if row.get("帖子正文部分"):
            continue
        note_id = note_id_from_url(row["帖子链接"])
        local = local_body_map.get(note_id)
        if not local:
            continue
        body, source_name = local
        row["帖子正文部分"] = body
        local_filled += 1
        local_sources[source_name] = local_sources.get(source_name, 0) + 1

    before_live_missing = sum(1 for row in rows if not row.get("帖子正文部分"))
    live_filled = 0
    live_errors = 0
    if args.live and before_live_missing:
        live_results = fetch_live_bodies(rows, limit=args.limit)
        for row in rows:
            if row.get("帖子正文部分"):
                continue
            note_id = note_id_from_url(row["帖子链接"])
            live = live_results.get(note_id)
            if not live:
                continue
            body = normalize_body(live.get("body", ""))
            if body:
                row["帖子正文部分"] = body
                if live.get("title"):
                    row["帖子名字"] = live["title"]
                live_filled += 1
            else:
                live_errors += 1

    missing = sum(1 for row in rows if not row.get("帖子正文部分"))
    meta = {
        "source": str(SOURCE_JSON),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "columns_deleted": ["评论方向", "帖主昵称", "粉丝数", "联系方式", "来源"],
        "fields": KEEP_FIELDS,
        "rows_total": len(rows),
        "initial_body_nonempty": sum(1 for row in source_rows if str(row.get("帖子正文部分") or "").strip()),
        "local_filled": local_filled,
        "local_sources": local_sources,
        "before_live_missing": before_live_missing,
        "live_enabled": args.live,
        "live_filled": live_filled,
        "live_errors_or_empty": live_errors,
        "missing_body_after": missing,
        "outputs": {
            "json": str(OUTPUT_JSON),
            "markdown": str(OUTPUT_MD),
            "inbox_markdown": str(INBOX_MD),
            "lark_fields": str(LARK_FIELDS_JSON),
            "lark_records": str(LARK_RECORDS_JSON),
        },
    }
    write_outputs(rows, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
