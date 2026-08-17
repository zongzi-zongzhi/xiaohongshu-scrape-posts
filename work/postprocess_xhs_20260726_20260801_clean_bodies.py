from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "outputs" / "xhs_insforge_incremental_merged_20260726_20260801.json"
OUT_MD = ROOT / "outputs" / "xhs_insforge_incremental_merged_20260726_20260801.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书建联线索池_新格式_增量合并_20260726-20260801.md")
FIELDS_JSON = ROOT / "work" / "xhs_incremental_merged_base_fields_20260726_20260801.json"
RECORDS_JSON = ROOT / "work" / "xhs_incremental_merged_records_payload_20260726_20260801.json"

FIELDS = ["发布时间", "帖子名字", "帖子链接", "帖子正文", "评论", "评论例子", "匹配关键词"]
NOTE_ID_RE = re.compile(r"/explore/([^/?#]+)")


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def note_id_from_url(url: Any) -> str:
    match = NOTE_ID_RE.search(str(url or ""))
    if match:
        return match.group(1)
    return str(url or "").split("?", 1)[0].rstrip("/")


def numericish(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 16:
        return False
    if not any(ch.isdigit() for ch in line):
        return False
    non_numeric = sum(1 for ch in line if not (ch.isdigit() or ch in ".,%+ -"))
    return non_numeric <= 2


def looks_like_recommend_feed(body: str) -> bool:
    lines = [line.strip() for line in str(body or "").splitlines() if line.strip()]
    if len(lines) < 120:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 20)
    numeric_lines = sum(1 for line in lines if numericish(line))
    if numeric_lines >= 35:
        return True
    if len(body) > 1200 and short_lines > 110:
        return True
    return False


def parse_time(row: dict[str, Any]) -> datetime:
    text = str(row.get("发布时间") or "")
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.min


def normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized = {field: str(row.get(field) or "").strip() for field in FIELDS}
    normalized["评论"] = ""
    return normalized


def write_outputs(rows: list[dict[str, str]], meta: dict[str, Any]) -> None:
    payload = {"meta": meta, "rows": rows}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "| " + " | ".join(FIELDS) + " |",
        "| " + " | ".join(["---"] * len(FIELDS)) + " |",
    ]
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


def main() -> int:
    data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    raw_rows = [row for row in data.get("rows", []) if isinstance(row, dict)]
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}

    removed: list[dict[str, str]] = []
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    duplicate_count = 0
    blank_body_count = 0

    for raw_row in raw_rows:
        row = normalize_row(raw_row)
        note_key = note_id_from_url(row["帖子链接"])
        if note_key in seen:
            duplicate_count += 1
            continue
        seen.add(note_key)
        if not row["帖子正文"]:
            blank_body_count += 1
            removed.append({"note_id": note_key, "title": row["帖子名字"], "reason": "blank_body"})
            continue
        if looks_like_recommend_feed(row["帖子正文"]):
            removed.append({"note_id": note_key, "title": row["帖子名字"], "reason": "recommend_feed_body"})
            continue
        cleaned.append(row)

    cleaned.sort(key=parse_time, reverse=True)
    missing_body_after = sum(1 for row in cleaned if not row["帖子正文"])
    meta["row_count"] = len(cleaned)
    meta["missing_body_after"] = missing_body_after
    meta["fields"] = FIELDS
    meta["postprocess_clean_bodies"] = {
        "script": str(Path(__file__).resolve()),
        "raw_rows": len(raw_rows),
        "kept_rows": len(cleaned),
        "removed_rows": len(removed),
        "removed": removed,
        "duplicates_skipped": duplicate_count,
        "blank_body_removed": blank_body_count,
        "rule": "remove rows whose body looks like Xiaohongshu recommendation feed text",
    }
    meta.setdefault("outputs", {})
    meta["outputs"].update(
        {
            "json": str(OUT_JSON),
            "markdown": str(OUT_MD),
            "inbox_markdown": str(INBOX_MD),
            "lark_fields": str(FIELDS_JSON),
            "lark_records": str(RECORDS_JSON),
        }
    )

    write_outputs(cleaned, meta)
    print(
        json.dumps(
            {
                "status": "complete",
                "raw_rows": len(raw_rows),
                "kept_rows": len(cleaned),
                "removed_rows": len(removed),
                "missing_body_after": missing_body_after,
                "duplicates_skipped": duplicate_count,
                "output_json": str(OUT_JSON),
                "inbox_md": str(INBOX_MD),
                "removed": removed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
