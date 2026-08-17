from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "xhs_insforge_expanded_leads_comments_7day_no_profile_20260721_20260727.json"


def note_id_from_url(url: str) -> str:
    match = re.search(r"/explore/([0-9a-f]{24})", str(url or ""))
    return match.group(1) if match else ""


def iter_dict_rows(obj: Any):
    if isinstance(obj, dict):
        if all(key in obj for key in ("帖子链接", "帖子正文部分")):
            yield obj
        for key in ("rows", "posts", "candidates", "items", "data", "records"):
            value = obj.get(key)
            if isinstance(value, list):
                for item in value:
                    yield from iter_dict_rows(item)
        fields = obj.get("fields")
        rows = obj.get("rows")
        if isinstance(fields, list) and isinstance(rows, list) and "帖子正文部分" in fields:
            for row in rows:
                if isinstance(row, list):
                    mapped = {field: row[index] if index < len(row) else "" for index, field in enumerate(fields)}
                    yield mapped
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dict_rows(item)


def row_body(row: dict[str, Any]) -> str:
    return str(
        row.get("帖子正文部分")
        or row.get("body")
        or row.get("正文")
        or row.get("desc")
        or row.get("description")
        or row.get("content")
        or ""
    ).strip()


def row_url(row: dict[str, Any]) -> str:
    return str(row.get("帖子链接") or row.get("url") or row.get("link") or "").strip()


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_rows = source["rows"]
    source_ids = [note_id_from_url(row["帖子链接"]) for row in source_rows]
    missing_ids = {
        note_id_from_url(row["帖子链接"])
        for row in source_rows
        if not str(row.get("帖子正文部分") or "").strip()
    }
    print({"source_rows": len(source_rows), "source_missing": len(missing_ids)})

    body_by_id: dict[str, tuple[str, str]] = {}
    for folder in (ROOT / "outputs", ROOT / "work"):
        for path in folder.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            added = 0
            for row in iter_dict_rows(data):
                body = row_body(row)
                url = row_url(row)
                note_id = str(row.get("note_id") or row.get("id") or note_id_from_url(url)).strip()
                if not note_id or not body:
                    continue
                if note_id not in body_by_id or len(body) > len(body_by_id[note_id][0]):
                    body_by_id[note_id] = (body, path.name)
                    added += 1
            if added:
                overlap = sum(1 for note_id in missing_ids if note_id in body_by_id and body_by_id[note_id][1] == path.name)
                print({"file": str(path.relative_to(ROOT)), "added_or_replaced": added, "missing_overlap_from_file": overlap})

    existing = sum(1 for row in source_rows if str(row.get("帖子正文部分") or "").strip())
    recoverable = sum(1 for note_id in missing_ids if note_id in body_by_id)
    print({"existing_body": existing, "recoverable_missing_from_local": recoverable, "still_need_live": len(missing_ids) - recoverable})
    for index, row in enumerate(source_rows, start=1):
        note_id = source_ids[index - 1]
        if note_id in missing_ids and note_id not in body_by_id:
            print({"need_live_index": index, "title": row["帖子名字"], "url": row["帖子链接"]})


if __name__ == "__main__":
    main()
