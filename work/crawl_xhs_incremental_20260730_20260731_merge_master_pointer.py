from __future__ import annotations

import json
import re
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any

import crawl_xhs_incremental_20260727_20260728_merge_existing as job


TZ = job.TZ
NOW = datetime.now(TZ)

OUTPUT_FIELDS = ["发布时间", "帖子名字", "帖子链接", "帖子正文", "评论", "评论例子", "匹配关键词"]
BODY_FIELD = "帖子正文"
OLD_BODY_FIELD = "帖子正文部分"

job.BASE_START = datetime(2026, 7, 25, 0, 0, 0, tzinfo=TZ)
job.BASE_END = datetime.combine(datetime(2026, 7, 30).date(), dt_time(23, 59, 59), tzinfo=TZ)
job.INCREMENTAL_START = datetime(2026, 7, 30, 0, 0, 0, tzinfo=TZ)
job.INCREMENTAL_END = NOW
job.TARGET = None
job.KEEP_FIELDS = OUTPUT_FIELDS

job.OLD_SOURCE_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260724_20260730.json"
job.OUT_JSON = job.OUT_DIR / "xhs_insforge_incremental_merged_20260725_20260731.json"
job.OUT_MD = job.OUT_DIR / "xhs_insforge_incremental_merged_20260725_20260731.md"
job.INBOX_MD = job.INBOX / "小红书建联线索池_新格式_增量合并_20260725-20260731.md"
job.FIELDS_JSON = job.WORK_DIR / "xhs_incremental_merged_base_fields_20260725_20260731.json"
job.RECORDS_JSON = job.WORK_DIR / "xhs_incremental_merged_records_payload_20260725_20260731.json"
job.INC_CACHE_JSON = job.OUT_DIR / "xhs_incremental_candidates_20260730_20260731.json"
job.VERIFY_STATE_JSON = job.WORK_DIR / "xhs_incremental_verify_required_state_20260730_20260731.json"
job.VERIFY_SCREENSHOT = job.WORK_DIR / "xhs_incremental_verify_required_20260730_20260731.png"

EXTRA_EXCLUDE = re.compile(
    r"(技术面|面还原|面试题|产品岗|算法岗|开发岗|工程师岗|应用岗|校招|秋招|春招|求职|简历|实习|招聘|面经|offer|OFFER|训练营|课程售卖)"
)
_original_hard_excluded = job.expanded.hard_excluded


def _text_blob(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ("帖子名字", "title", "帖子正文", "帖子正文部分", "desc", "匹配关键词", "keyword")
    )


def hard_excluded(row: dict[str, Any]) -> bool:
    return _original_hard_excluded(row) or bool(EXTRA_EXCLUDE.search(_text_blob(row)))


job.expanded.hard_excluded = hard_excluded


def body_of(row: dict[str, Any]) -> str:
    return job.normalize_body(row.get(BODY_FIELD) or row.get(OLD_BODY_FIELD) or "")


def load_old_rows() -> list[dict[str, Any]]:
    data = json.loads(Path(job.OLD_SOURCE_JSON).read_text(encoding="utf-8"))
    source_rows = data.get("rows", [])
    rows: list[dict[str, Any]] = []
    for source_row in source_rows:
        if not isinstance(source_row, dict):
            continue
        note_id = job.note_id_from_url(source_row.get("帖子链接"))
        dt = job.parse_row_dt(
            {"发布时间": source_row.get("发布时间"), "帖子链接": source_row.get("帖子链接"), "note_id": note_id}
        )
        if not dt or not (job.BASE_START <= dt <= job.BASE_END):
            continue
        row = {
            "发布时间": str(source_row.get("发布时间") or "").strip(),
            "帖子名字": str(source_row.get("帖子名字") or "").strip(),
            "帖子链接": str(source_row.get("帖子链接") or "").strip(),
            "帖子正文": body_of(source_row),
            "评论": "",
            "评论例子": str(source_row.get("评论例子") or "").strip(),
            "匹配关键词": str(source_row.get("匹配关键词") or "").strip(),
            "note_id": note_id,
            "published_at": dt.isoformat(),
        }
        if hard_excluded(row):
            continue
        rows.append(row)
    return rows


def make_incremental_final_row(row: dict[str, Any]) -> dict[str, Any]:
    level, priority, mention = job.expanded.classify(row)
    copied = dict(row)
    copied["线索等级"] = level
    copied["评论优先级"] = priority
    copied["是否直接提InsForge"] = mention
    _, comment = job.expanded.comment_plan(copied)
    dt = job.parse_row_dt(row)
    return {
        "发布时间": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "",
        "帖子名字": str(row.get("帖子名字") or "").strip(),
        "帖子链接": str(row.get("帖子链接") or "").strip(),
        "帖子正文": body_of(row),
        "评论": "",
        "评论例子": job.humanize_comment(comment),
        "匹配关键词": str(row.get("匹配关键词") or "").strip(),
        "note_id": row.get("note_id") or job.note_id_from_url(row.get("帖子链接")),
        "published_at": dt.isoformat() if dt else "",
        "来源": row.get("来源", ""),
    }


def merge_rows(old_rows: list[dict[str, Any]], inc_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], prefer: bool = False) -> None:
        note_id = str(row.get("note_id") or job.note_id_from_url(row.get("帖子链接")) or row.get("帖子链接") or "")
        if not note_id:
            return
        existing = merged.get(note_id)
        if not existing:
            copied = dict(row)
            copied["帖子正文"] = body_of(copied)
            copied["评论"] = ""
            merged[note_id] = copied
            return
        for field in ["发布时间", "帖子名字", "帖子链接", "评论例子"]:
            if prefer and row.get(field):
                existing[field] = row[field]
            elif not existing.get(field) and row.get(field):
                existing[field] = row[field]
        existing["评论"] = ""
        existing["匹配关键词"] = job.merge_keywords(existing.get("匹配关键词"), row.get("匹配关键词"))
        old_body = body_of(existing)
        new_body = body_of(row)
        if new_body and (prefer or len(new_body) > len(old_body)):
            existing["帖子正文"] = new_body
        if row.get("published_at"):
            existing["published_at"] = row["published_at"]

    for row in old_rows:
        add(row, prefer=False)
    for row in inc_rows:
        add(row, prefer=True)

    rows = list(merged.values())
    rows.sort(key=lambda row: job.parse_row_dt(row) or job.BASE_START, reverse=True)
    return rows


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    final_rows = [{field: row.get(field, "") for field in OUTPUT_FIELDS} for row in rows]
    job.OUT_JSON.write_text(json.dumps({"meta": meta, "rows": final_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 小红书 InsForge 建联线索池（新格式增量合并版）", ""]
    lines.append("| " + " | ".join(OUTPUT_FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(OUTPUT_FIELDS)) + " |")
    for row in final_rows:
        cells = []
        for field in OUTPUT_FIELDS:
            if field == "帖子链接" and row.get(field):
                cells.append(f"[打开]({row[field]})")
            else:
                cells.append(job.markdown_escape(row.get(field, "")))
        lines.append("| " + " | ".join(cells) + " |")
    markdown = "\n".join(lines) + "\n"
    job.OUT_MD.write_text(markdown, encoding="utf-8")
    job.INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    job.INBOX_MD.write_text(markdown, encoding="utf-8")

    job.FIELDS_JSON.write_text(
        json.dumps([{"name": field, "type": "text"} for field in OUTPUT_FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    job.RECORDS_JSON.write_text(
        json.dumps(
            {"fields": OUTPUT_FIELDS, "rows": [[row.get(field, "") for field in OUTPUT_FIELDS] for row in final_rows]},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


job.load_old_rows = load_old_rows
job.make_incremental_final_row = make_incremental_final_row
job.merge_rows = merge_rows
job.write_outputs = write_outputs


if __name__ == "__main__":
    raise SystemExit(job.main())
