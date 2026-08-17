from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
INBOX = Path(r"D:\czj note\00_Inbox")
CURRENT_OUTPUTS = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-30\insforge-xhs-daily-crawl-handoff\outputs")

RUN_START_LABEL = "20260722"
RUN_END_LABEL = "20260731"

OUT_JSON = OUT_DIR / f"xhs_insforge_all_crawled_posts_master_{RUN_START_LABEL}_{RUN_END_LABEL}.json"
OUT_MD = OUT_DIR / f"xhs_insforge_all_crawled_posts_master_{RUN_START_LABEL}_{RUN_END_LABEL}.md"
INBOX_MD = INBOX / f"小红书InsForge_所有爬取帖子总表_{RUN_START_LABEL}-{RUN_END_LABEL}.md"
FIELDS_JSON = WORK_DIR / f"xhs_all_crawled_posts_master_base_fields_{RUN_START_LABEL}_{RUN_END_LABEL}.json"
RECORDS_JSON = WORK_DIR / f"xhs_all_crawled_posts_master_records_payload_{RUN_START_LABEL}_{RUN_END_LABEL}.json"

TZ = timezone(timedelta(hours=8))
NOTE_RE = re.compile(r"/explore/([0-9a-f]{24})")

OUTPUT_FIELDS = [
    "发布时间",
    "帖子名字",
    "帖子链接",
    "帖子正文",
    "评论",
    "评论例子",
    "匹配关键词",
    "来源类型",
    "来源文件",
    "来源数量",
    "note_id",
    "帖主昵称",
    "帖主主页链接",
    "点赞数",
    "收藏数",
    "评论数",
]

SKIP_NAME_PARTS = [
    "author_profiles_cache",
    "all_crawled_posts_master",
    "master_pointer",
    "lark_base",
]


def note_id_from_url(value: Any) -> str:
    match = NOTE_RE.search(str(value or ""))
    return match.group(1) if match else ""


def note_time(note_id: str) -> datetime | None:
    text = str(note_id or "").strip()
    if len(text) < 8:
        return None
    try:
        return datetime.fromtimestamp(int(text[:8], 16), TZ)
    except Exception:
        return None


def parse_dt(value: Any, note_id: str = "") -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(TZ)
    text = str(value or "").strip()
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
    return note_time(note_id)


def format_dt(value: Any, note_id: str = "") -> str:
    dt = parse_dt(value, note_id)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def normalize_body(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def to_int(value: Any) -> int:
    text = str(value or "").strip().lower().replace(",", "")
    if not text:
        return 0
    multiplier = 1
    if "万" in text:
        multiplier = 10000
        text = text.replace("万", "")
    elif "k" in text:
        multiplier = 1000
        text = text.replace("k", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return 0
    try:
        return int(float(match.group(0)) * multiplier)
    except Exception:
        return 0


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def merge_words(*values: Any, limit: int = 40) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        else:
            parts.extend(str(item).strip() for item in str(value or "").replace(";", " ").split() if str(item).strip())
    return " ".join(list(dict.fromkeys(parts))[:limit])


def list_rows(data: Any) -> tuple[str, list[dict[str, Any]]]:
    if isinstance(data, list):
        return "list", [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return "", []
    for key in ("rows", "posts", "records", "items", "candidates"):
        value = data.get(key)
        if isinstance(value, list):
            return key, [row for row in value if isinstance(row, dict)]
        if key == "candidates" and isinstance(value, dict):
            return "candidates", [row for row in value.values() if isinstance(row, dict)]
    return "", []


def source_type(path: Path, list_key: str) -> str:
    name = path.name
    if "candidates" in name or list_key == "candidates":
        return "候选缓存"
    if "incremental_merged" in name:
        return "滚动合并总表"
    if "expanded" in name or "minimal_full_body" in name or "comment_examples" in name:
        return "正式线索表"
    if "title_body" in name:
        return "正文补全结果"
    if "pain_posts" in name:
        return "早期痛点结果"
    return "帖子结果"


def row_to_record(row: dict[str, Any], path: Path, list_key: str) -> dict[str, Any] | None:
    note_id = str(row.get("note_id") or row.get("id") or "").strip()
    url = str(row.get("帖子链接") or row.get("url") or row.get("link") or "").strip()
    if not note_id:
        note_id = note_id_from_url(url)
    token = str(row.get("xsec_token") or row.get("xsecToken") or "").strip()
    if not url and note_id:
        suffix = f"?xsec_token={token}&xsec_source=pc_search" if token else ""
        url = f"https://www.xiaohongshu.com/explore/{note_id}{suffix}"
    if not note_id and not url:
        return None

    title = str(row.get("帖子名字") or row.get("帖子标题") or row.get("title") or "").strip()
    if not title:
        return None

    body = normalize_body(
        row.get("帖子正文")
        or row.get("帖子正文部分")
        or row.get("desc")
        or row.get("description")
        or row.get("note_desc")
        or row.get("content")
        or row.get("text")
        or row.get("正文")
        or ""
    )
    published = format_dt(row.get("发布时间") or row.get("published_at") or row.get("publish_time") or row.get("created_at"), note_id)
    comment_example = str(row.get("评论例子") or row.get("建议评论") or "").strip()
    keywords = merge_words(row.get("匹配关键词"), row.get("matched_keywords"), row.get("keyword"), row.get("variants"))

    return {
        "发布时间": published,
        "帖子名字": title,
        "帖子链接": url,
        "帖子正文": body,
        "评论": "",
        "评论例子": comment_example,
        "匹配关键词": keywords,
        "来源类型": source_type(path, list_key),
        "来源文件": path.name,
        "来源数量": "1",
        "note_id": note_id,
        "帖主昵称": str(row.get("帖主昵称") or row.get("author") or row.get("nickname") or "").strip(),
        "帖主主页链接": str(row.get("帖主主页链接") or row.get("profile_url") or "").strip(),
        "点赞数": str(to_int(row.get("点赞") or row.get("liked_count") or row.get("likedCount"))),
        "收藏数": str(to_int(row.get("收藏") or row.get("collected_count") or row.get("collectedCount"))),
        "评论数": str(to_int(row.get("评论数") or row.get("评论") or row.get("comment_count") or row.get("commentCount"))),
        "_source_file_set": {path.name},
        "_source_type_set": {source_type(path, list_key)},
    }


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for field in ["发布时间", "帖子名字", "帖子链接", "评论例子", "帖主昵称", "帖主主页链接"]:
        if incoming.get(field) and not existing.get(field):
            existing[field] = incoming[field]

    if len(str(incoming.get("帖子正文") or "")) > len(str(existing.get("帖子正文") or "")):
        existing["帖子正文"] = incoming["帖子正文"]
    existing["评论"] = ""
    existing["匹配关键词"] = merge_words(existing.get("匹配关键词"), incoming.get("匹配关键词"))

    for field in ["点赞数", "收藏数", "评论数"]:
        existing[field] = str(max(to_int(existing.get(field)), to_int(incoming.get(field))))

    existing["_source_file_set"].update(incoming.get("_source_file_set", set()))
    existing["_source_type_set"].update(incoming.get("_source_type_set", set()))
    existing["来源文件"] = "; ".join(sorted(existing["_source_file_set"]))
    existing["来源类型"] = "; ".join(sorted(existing["_source_type_set"]))
    existing["来源数量"] = str(len(existing["_source_file_set"]))


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    source_stats: list[dict[str, Any]] = []

    for path in sorted(OUT_DIR.glob("xhs*.json"), key=lambda item: item.stat().st_mtime):
        if any(part in path.name for part in SKIP_NAME_PARTS):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        list_key, rows = list_rows(data)
        if not rows:
            continue
        seen_in_file = 0
        for row in rows:
            record = row_to_record(row, path, list_key)
            if not record:
                continue
            key = record.get("note_id") or record.get("帖子链接")
            if not key:
                continue
            seen_in_file += 1
            if key not in merged:
                merged[key] = record
            else:
                merge_record(merged[key], record)
        source_stats.append({"file": path.name, "list_key": list_key, "rows": len(rows), "usable_posts": seen_in_file})

    rows = list(merged.values())
    for row in rows:
        row["来源文件"] = "; ".join(sorted(row.pop("_source_file_set", set())))
        row["来源类型"] = "; ".join(sorted(row.pop("_source_type_set", set())))
        row["来源数量"] = str(len(row["来源文件"].split("; "))) if row["来源文件"] else "0"
    rows.sort(key=lambda row: parse_dt(row.get("发布时间"), row.get("note_id")) or datetime.min.replace(tzinfo=TZ), reverse=True)

    final_rows = [{field: row.get(field, "") for field in OUTPUT_FIELDS} for row in rows]
    meta = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "All local Xiaohongshu post-like JSON outputs produced for the InsForge crawl task, excluding author profile caches, lark upload metadata, and pointer files.",
        "run_file_window": {"start": RUN_START_LABEL, "end": RUN_END_LABEL},
        "source_file_count": len(source_stats),
        "source_stats": source_stats,
        "dedupe_key": "note_id, falling back to post URL",
        "row_count": len(final_rows),
        "missing_body_count": sum(1 for row in final_rows if not row.get("帖子正文")),
        "fields": OUTPUT_FIELDS,
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

    lines = ["# 小红书 InsForge 所有爬取帖子总表", ""]
    lines.append("| " + " | ".join(OUTPUT_FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(OUTPUT_FIELDS)) + " |")
    for row in rows:
        cells = []
        for field in OUTPUT_FIELDS:
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
        json.dumps([{"name": field, "type": "text"} for field in OUTPUT_FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    RECORDS_JSON.write_text(
        json.dumps({"fields": OUTPUT_FIELDS, "rows": [[row.get(field, "") for field in OUTPUT_FIELDS] for row in rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    CURRENT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (CURRENT_OUTPUTS / OUT_JSON.name).write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    (CURRENT_OUTPUTS / OUT_MD.name).write_text(OUT_MD.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    rows, meta = build()
    write_outputs(rows, meta)
    print(
        json.dumps(
            {
                "status": "complete",
                "rows": len(rows),
                "missing_body_count": meta["missing_body_count"],
                "source_file_count": meta["source_file_count"],
                "output_json": str(OUT_JSON),
                "output_md": str(OUT_MD),
                "inbox_md": str(INBOX_MD),
                "fields_json": str(FIELDS_JSON),
                "records_json": str(RECORDS_JSON),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
