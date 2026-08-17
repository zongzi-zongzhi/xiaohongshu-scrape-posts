from __future__ import annotations

import argparse
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


def default_path(meta: dict[str, Any], key: str, fallback: Path) -> Path:
    outputs = meta.get("outputs", {}) if isinstance(meta.get("outputs"), dict) else {}
    value = outputs.get(key)
    return Path(value) if value else fallback


def write_outputs(
    rows: list[dict[str, str]],
    meta: dict[str, Any],
    *,
    output_json: Path,
    output_md: Path,
    inbox_md: Path,
    fields_json: Path,
    records_json: Path,
) -> None:
    payload = {"meta": meta, "rows": rows}
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 小红书 InsForge 建联线索池（新格式增量合并版）",
        "",
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
    output_md.write_text(markdown, encoding="utf-8")
    inbox_md.parent.mkdir(parents=True, exist_ok=True)
    inbox_md.write_text(markdown, encoding="utf-8")

    fields_json.write_text(
        json.dumps([{"name": field, "type": "text"} for field in FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    records_json.write_text(
        json.dumps({"fields": FIELDS, "rows": [[row.get(field, "") for field in FIELDS] for row in rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--inbox-md", type=Path)
    parser.add_argument("--fields-json", type=Path)
    parser.add_argument("--records-json", type=Path)
    args = parser.parse_args()

    source_json = args.source_json if args.source_json.is_absolute() else ROOT / args.source_json
    data = json.loads(source_json.read_text(encoding="utf-8"))
    raw_rows = [row for row in data.get("rows", []) if isinstance(row, dict)]
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}

    output_md = args.output_md or default_path(meta, "markdown", source_json.with_suffix(".md"))
    inbox_md = args.inbox_md or default_path(meta, "inbox_markdown", source_json.with_suffix(".md"))
    fields_json = args.fields_json or default_path(meta, "lark_fields", ROOT / "work" / f"{source_json.stem}_fields.json")
    records_json = args.records_json or default_path(meta, "lark_records", ROOT / "work" / f"{source_json.stem}_records_payload.json")

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
            "json": str(source_json),
            "markdown": str(output_md),
            "inbox_markdown": str(inbox_md),
            "lark_fields": str(fields_json),
            "lark_records": str(records_json),
        }
    )

    write_outputs(
        cleaned,
        meta,
        output_json=source_json,
        output_md=output_md,
        inbox_md=inbox_md,
        fields_json=fields_json,
        records_json=records_json,
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "raw_rows": len(raw_rows),
                "kept_rows": len(cleaned),
                "removed_rows": len(removed),
                "missing_body_after": missing_body_after,
                "duplicates_skipped": duplicate_count,
                "output_json": str(source_json),
                "inbox_md": str(inbox_md),
                "removed": removed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
