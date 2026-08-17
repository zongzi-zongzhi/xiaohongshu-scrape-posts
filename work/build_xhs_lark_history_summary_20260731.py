from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
INBOX = Path(r"D:\czj note\00_Inbox")
CURRENT_OUTPUTS = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-30\insforge-xhs-daily-crawl-handoff\outputs")

SOURCE_JSON = OUT_DIR / "xhs_lark_history_bases_records_20260731.json"
START_LABEL = "20260721"
END_LABEL = "20260731"

OUT_JSON = OUT_DIR / f"xhs_insforge_lark_history_summary_{START_LABEL}_{END_LABEL}.json"
OUT_MD = OUT_DIR / f"xhs_insforge_lark_history_summary_{START_LABEL}_{END_LABEL}.md"
INBOX_MD = INBOX / f"小红书InsForge_飞书历史表汇总_{START_LABEL}-{END_LABEL}.md"
FIELDS_JSON = WORK_DIR / f"xhs_insforge_lark_history_summary_base_fields_{START_LABEL}_{END_LABEL}.json"
RECORDS_JSON = WORK_DIR / f"xhs_insforge_lark_history_summary_records_payload_{START_LABEL}_{END_LABEL}.json"

TZ = timezone(timedelta(hours=8))
NOTE_RE = re.compile(r"/explore/([0-9a-f]{24})")
FIELDS = ["发布时间", "帖子名字", "帖子链接", "帖子正文", "评论", "评论例子", "匹配关键词"]
EXCLUDE_META_PARTS = ["all_crawled_posts_master"]


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def note_id_from_url(value: Any) -> str:
    match = NOTE_RE.search(str(value or ""))
    return match.group(1) if match else ""


def parse_dt(value: Any, note_id: str = "") -> datetime | None:
    text = normalize_text(value)
    if text:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=TZ)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(TZ)
        except Exception:
            pass
    if note_id and len(note_id) >= 8:
        try:
            return datetime.fromtimestamp(int(note_id[:8], 16), TZ)
        except Exception:
            return None
    return None


def format_dt(value: Any, note_id: str = "") -> str:
    dt = parse_dt(value, note_id)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def merge_keywords(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        else:
            parts.extend(str(item).strip() for item in str(value or "").replace(";", " ").split() if str(item).strip())
    return " ".join(list(dict.fromkeys(parts))[:32])


def normalized_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    meta_file = normalize_text(raw.get("_lark_meta_file"))
    if any(part in meta_file for part in EXCLUDE_META_PARTS):
        return None
    url = normalize_text(raw.get("帖子链接"))
    note_id = note_id_from_url(url)
    if not note_id or not url:
        return None
    body = normalize_text(raw.get("帖子正文") or raw.get("帖子正文部分"))
    return {
        "发布时间": format_dt(raw.get("发布时间"), note_id),
        "帖子名字": normalize_text(raw.get("帖子名字")),
        "帖子链接": url,
        "帖子正文": body,
        "评论": "",
        "评论例子": normalize_text(raw.get("评论例子") or raw.get("建议评论")),
        "匹配关键词": merge_keywords(raw.get("匹配关键词")),
        "note_id": note_id,
        "_lark_meta_file": meta_file,
        "_lark_base_name": normalize_text(raw.get("_lark_base_name")),
        "_lark_base_url": normalize_text(raw.get("_lark_base_url")),
    }


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for field in ["发布时间", "帖子名字", "帖子链接"]:
        if incoming.get(field) and not existing.get(field):
            existing[field] = incoming[field]
    if len(incoming.get("帖子正文", "")) > len(existing.get("帖子正文", "")):
        existing["帖子正文"] = incoming["帖子正文"]
    if len(incoming.get("评论例子", "")) > len(existing.get("评论例子", "")):
        existing["评论例子"] = incoming["评论例子"]
    existing["评论"] = ""
    existing["匹配关键词"] = merge_keywords(existing.get("匹配关键词"), incoming.get("匹配关键词"))
    existing["_source_files"].add(incoming.get("_lark_meta_file", ""))
    existing["_source_bases"].add(incoming.get("_lark_base_url", ""))
    old_dt = parse_dt(existing.get("发布时间"), existing.get("note_id", ""))
    new_dt = parse_dt(incoming.get("发布时间"), incoming.get("note_id", ""))
    if new_dt and (not old_dt or new_dt > old_dt):
        existing["发布时间"] = incoming["发布时间"]


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    raw_rows = [row for row in source.get("rows", []) if isinstance(row, dict)]
    merged: dict[str, dict[str, Any]] = {}
    included_raw_count = 0
    excluded_raw_count = 0
    source_files: set[str] = set()
    source_bases: set[str] = set()
    for raw in raw_rows:
        row = normalized_row(raw)
        if row is None:
            excluded_raw_count += 1
            continue
        included_raw_count += 1
        source_files.add(row["_lark_meta_file"])
        source_bases.add(row["_lark_base_url"])
        key = row["note_id"]
        if key not in merged:
            row["_source_files"] = {row.get("_lark_meta_file", "")}
            row["_source_bases"] = {row.get("_lark_base_url", "")}
            merged[key] = row
        else:
            merge_record(merged[key], row)

    rows = list(merged.values())
    rows.sort(key=lambda item: parse_dt(item.get("发布时间"), item.get("note_id", "")) or datetime.min.replace(tzinfo=TZ), reverse=True)
    final_rows = [{field: row.get(field, "") for field in FIELDS} for row in rows]
    meta = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source_json": str(SOURCE_JSON),
        "source_rule": "Only historical Feishu Base records are included. The locally-built all_crawled_posts_master Base is excluded to keep this as a Feishu-history summary.",
        "raw_rows_total": len(raw_rows),
        "raw_rows_included": included_raw_count,
        "raw_rows_excluded": excluded_raw_count,
        "source_base_count": len([item for item in source_bases if item]),
        "source_meta_files": sorted(item for item in source_files if item),
        "dedupe_key": "Xiaohongshu note_id parsed from 帖子链接",
        "row_count": len(final_rows),
        "fields": FIELDS,
        "blank_comment_count": sum(1 for row in final_rows if not row.get("评论")),
        "missing_body_count": sum(1 for row in final_rows if not row.get("帖子正文")),
        "missing_comment_example_count": sum(1 for row in final_rows if not row.get("评论例子")),
        "outputs": {
            "json": str(OUT_JSON),
            "markdown": str(OUT_MD),
            "inbox_markdown": str(INBOX_MD),
            "lark_fields": str(FIELDS_JSON),
            "lark_records": str(RECORDS_JSON),
        },
    }
    return final_rows, meta


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    OUT_JSON.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 小红书 InsForge 飞书历史表汇总", ""]
    lines.append("| " + " | ".join(FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(FIELDS)) + " |")
    for row in rows:
        cells = []
        for field in FIELDS:
            if field == "帖子链接" and row.get(field):
                cells.append(f"[打开]({row[field]})")
            else:
                cells.append(markdown_escape(row.get(field, "")))
        lines.append("| " + " | ".join(cells) + " |")
    markdown = "\n".join(lines) + "\n"
    OUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(markdown, encoding="utf-8")

    FIELDS_JSON.write_text(
        json.dumps([{"name": field, "type": "text"} for field in FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    RECORDS_JSON.write_text(
        json.dumps({"fields": FIELDS, "rows": [[row.get(field, "") for field in FIELDS] for row in rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    CURRENT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (CURRENT_OUTPUTS / OUT_JSON.name).write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    (CURRENT_OUTPUTS / OUT_MD.name).write_text(OUT_MD.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    rows, meta = build()
    write_outputs(rows, meta)
    print(json.dumps({"status": "complete", **meta}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
