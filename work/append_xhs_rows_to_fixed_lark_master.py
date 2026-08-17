from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import xhs_rules_doc
except Exception:
    xhs_rules_doc = None


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
POINTER_JSON = OUT_DIR / "xhs_insforge_master_pointer.json"
RULES = xhs_rules_doc.RULES if xhs_rules_doc is not None else None

FIXED_BASE_DOMAIN = os.environ.get("XHS_LARK_BASE_DOMAIN", "").strip()
FIXED_BASE_TOKEN = os.environ.get("XHS_LARK_BASE_TOKEN", "").strip()
FIXED_TABLE_ID = os.environ.get("XHS_LARK_TABLE_ID", "").strip()
FIXED_TABLE_URL = f"{FIXED_BASE_DOMAIN}/base/{FIXED_BASE_TOKEN}?table={FIXED_TABLE_ID}"

BATCH_SIZE = 50
APPEND_LIMIT = RULES.append_limit if RULES is not None else 50
APPEND_MIN = RULES.append_min if RULES is not None else 25
KEEP_FIELDS = RULES.output_fields if RULES is not None and RULES.output_fields else ["发布时间", "帖子名字", "帖子链接", "评论", "匹配关键词", "备注"]
REQUIRED_WRITE_FIELDS = [field for field in KEEP_FIELDS if field != "备注"]
KEYWORD_ALIASES = ["匹配关键词", "关键词", "keyword", "keywords"]
TITLE_ALIASES = ["帖子名字", "帖子标题", "title", "标题"]
TIME_ALIASES = ["发布时间", "发布时间文本", "publish_time", "published_at"]
LINK_ALIASES = ["帖子链接", "链接", "url", "note_url", "xhs_url"]
FINAL_EXCLUDE_RE = re.compile(
    r"(GitHub\s*热榜|github\s*热榜|GitHub近期热门|GitHub热门|GitHub爆火|GitHub增量榜|"
    r"AI日报|项目榜|开源热榜|热榜|TOP5|排行榜|榜单|工具清单|热门项目)",
    re.IGNORECASE,
)

NOTE_ID_RE = re.compile(r"/(?:explore|discovery/item)/([^/?#]+)")
TZ = dt.timezone(dt.timedelta(hours=8))


def parse_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def run_lark(args: list[str], *, retries: int = 1) -> dict[str, Any]:
    cmd = ["lark-cli.cmd", *args, "--as", "user", "--format", "json"]
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
        if proc.returncode == 0:
            return parse_json(proc.stdout)
        merged = f"{proc.stdout}\n{proc.stderr}"
        if "1254291" in merged and attempt < retries:
            time.sleep(2 + attempt)
            continue
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{merged}")
    raise RuntimeError("unreachable")


def first_text(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def note_key(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    match = NOTE_ID_RE.search(text)
    if match:
        return match.group(1)
    return text.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def final_excluded(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key) or "") for key in [*TITLE_ALIASES, *KEYWORD_ALIASES])
    return bool(FINAL_EXCLUDE_RE.search(text))


def extract_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
        return list(rows)
    fields = data.get("fields")
    if isinstance(fields, list) and isinstance(rows, list):
        extracted: list[dict[str, Any]] = []
        for raw_row in rows:
            if not isinstance(raw_row, list):
                continue
            extracted.append({str(field): raw_row[index] if index < len(raw_row) else "" for index, field in enumerate(fields)})
        return extracted
    return []


def load_pointer() -> dict[str, Any]:
    if not POINTER_JSON.exists():
        return {}
    return json.loads(POINTER_JSON.read_text(encoding="utf-8"))


def configure_fixed_master(pointer: dict[str, Any]) -> None:
    global FIXED_BASE_DOMAIN, FIXED_BASE_TOKEN, FIXED_TABLE_ID, FIXED_TABLE_URL

    if not FIXED_BASE_TOKEN:
        FIXED_BASE_TOKEN = str(pointer.get("fixed_master_base_token") or "").strip()
    if not FIXED_TABLE_ID:
        FIXED_TABLE_ID = str(pointer.get("fixed_master_table_id") or pointer.get("source_feishu_table_id") or "").strip()
    if not FIXED_BASE_DOMAIN:
        fixed_url = str(pointer.get("fixed_master_base_url") or pointer.get("source_feishu_base_url") or "").strip()
        parsed = urlparse(fixed_url)
        if parsed.scheme and parsed.netloc:
            FIXED_BASE_DOMAIN = f"{parsed.scheme}://{parsed.netloc}"

    missing = [
        name
        for name, value in {
            "XHS_LARK_BASE_DOMAIN or pointer.fixed_master_base_url": FIXED_BASE_DOMAIN,
            "XHS_LARK_BASE_TOKEN or pointer.fixed_master_base_token": FIXED_BASE_TOKEN,
            "XHS_LARK_TABLE_ID or pointer.fixed_master_table_id": FIXED_TABLE_ID,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing fixed Feishu master configuration: {missing}")
    FIXED_TABLE_URL = f"{FIXED_BASE_DOMAIN}/base/{FIXED_BASE_TOKEN}?table={FIXED_TABLE_ID}"


def source_from_pointer(pointer: dict[str, Any]) -> Path:
    source = str(pointer.get("source_json") or "").strip()
    if not source:
        raise RuntimeError(f"pointer has no source_json: {POINTER_JSON}")
    return Path(source)


def load_source_rows(source_json: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    data = json.loads(source_json.read_text(encoding="utf-8"))
    raw_rows = extract_rows(data)
    normalized: list[dict[str, str]] = []
    skipped_no_link = 0
    skipped_final_excluded = 0
    for raw_row in raw_rows:
        if final_excluded(raw_row):
            skipped_final_excluded += 1
            continue
        link = first_text(raw_row, LINK_ALIASES)
        if not note_key(link):
            skipped_no_link += 1
            continue
        base_row = {
            "发布时间": first_text(raw_row, TIME_ALIASES),
            "帖子名字": first_text(raw_row, TITLE_ALIASES),
            "帖子链接": link,
            "评论": "",
            "匹配关键词": first_text(raw_row, KEYWORD_ALIASES),
            "备注": "",
        }
        row = {field: str(base_row.get(field, raw_row.get(field, "")) or "").strip() for field in KEEP_FIELDS}
        if "评论" in row:
            row["评论"] = ""
        if "备注" in row:
            row["备注"] = ""
        normalized.append(row)
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    meta = meta if isinstance(meta, dict) else {}
    meta["source_raw_rows"] = len(raw_rows)
    meta["source_rows_without_link"] = skipped_no_link
    meta["source_rows_final_excluded"] = skipped_final_excluded
    return normalized, meta


def existing_note_keys() -> tuple[set[str], int, list[dict[str, Any]]]:
    offset = 0
    keys: set[str] = set()
    total_seen = 0
    pages: list[dict[str, Any]] = []
    while True:
        result = run_lark(
            [
                "base",
                "+record-list",
                "--base-token",
                FIXED_BASE_TOKEN,
                "--table-id",
                FIXED_TABLE_ID,
                "--limit",
                "200",
                "--offset",
                str(offset),
                "--field-id",
                "帖子链接",
            ],
            retries=2,
        )
        data = result.get("data", {}) if isinstance(result, dict) else {}
        fields = data.get("fields") or []
        values = data.get("data") or []
        has_more = bool(data.get("has_more"))
        link_index = fields.index("帖子链接") if "帖子链接" in fields else 0
        page_count = 0
        for value_row in values:
            if not isinstance(value_row, list) or link_index >= len(value_row):
                continue
            key = note_key(value_row[link_index])
            if key:
                keys.add(key)
            page_count += 1
        total_seen += page_count
        pages.append({"offset": offset, "count": page_count, "has_more": has_more})
        if not has_more or not values:
            break
        offset += len(values)
    return keys, total_seen, pages


def fixed_table_field_names() -> list[str]:
    result = run_lark(
        [
            "base",
            "+field-list",
            "--base-token",
            FIXED_BASE_TOKEN,
            "--table-id",
            FIXED_TABLE_ID,
        ],
        retries=2,
    )
    data = result.get("data", {}) if isinstance(result, dict) else {}
    fields = data.get("fields") or []
    names: list[str] = []
    for field in fields:
        if isinstance(field, dict) and field.get("name"):
            names.append(str(field["name"]))
    return names


def resolve_write_fields(existing_field_names: list[str]) -> tuple[list[str], list[str]]:
    existing = set(existing_field_names)
    missing_required = [field for field in REQUIRED_WRITE_FIELDS if field not in existing]
    if missing_required:
        raise RuntimeError(f"fixed Feishu table is missing required fields: {missing_required}; existing={existing_field_names}")
    write_fields = [field for field in KEEP_FIELDS if field in existing]
    missing_optional = [field for field in KEEP_FIELDS if field not in existing and field not in REQUIRED_WRITE_FIELDS]
    return write_fields, missing_optional


def unique_new_rows(rows: list[dict[str, str]], existing_keys: set[str], write_fields: list[str]) -> tuple[list[dict[str, str]], int]:
    pending: list[dict[str, str]] = []
    seen_this_run: set[str] = set()
    duplicate_count = 0
    for row in rows:
        key = note_key(row.get("帖子链接"))
        if not key:
            continue
        if key in existing_keys or key in seen_this_run:
            duplicate_count += 1
            continue
        seen_this_run.add(key)
        pending.append({field: row.get(field, "") for field in write_fields})
    return pending, duplicate_count


def write_payload(rows: list[dict[str, str]], run_tag: str, write_fields: list[str]) -> Path:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    path = WORK_DIR / f"xhs_fixed_master_append_payload_{run_tag}.json"
    payload = {"fields": write_fields, "rows": [[row.get(field, "") for field in write_fields] for row in rows]}
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def batch_append(rows: list[dict[str, str]], run_tag: str, write_fields: list[str]) -> tuple[int, list[str]]:
    uploaded = 0
    chunk_paths: list[str] = []
    for start in range(0, len(rows), BATCH_SIZE):
        chunk = rows[start : start + BATCH_SIZE]
        chunk_path = WORK_DIR / f"xhs_fixed_master_append_payload_{run_tag}_{start:03d}.json"
        payload = {"fields": write_fields, "rows": [[row.get(field, "") for field in write_fields] for row in chunk]}
        chunk_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        chunk_paths.append(str(chunk_path))
        run_lark(
            [
                "base",
                "+record-batch-create",
                "--base-token",
                FIXED_BASE_TOKEN,
                "--table-id",
                FIXED_TABLE_ID,
                "--json",
                f"@{chunk_path.relative_to(ROOT).as_posix()}",
            ],
            retries=2,
        )
        uploaded += len(chunk)
        print(json.dumps({"uploaded": uploaded, "total_to_append": len(rows)}, ensure_ascii=False), flush=True)
        time.sleep(0.3)
    return uploaded, chunk_paths


def update_pointer(pointer: dict[str, Any], source_json: Path, source_meta: dict[str, Any], append_meta: dict[str, Any]) -> None:
    source_json = source_json.resolve()
    outputs = source_meta.get("outputs", {}) if isinstance(source_meta.get("outputs"), dict) else {}
    source_markdown = str(outputs.get("inbox_markdown") or outputs.get("markdown") or pointer.get("source_markdown") or "")
    base_window = source_meta.get("base_window", {}) if isinstance(source_meta.get("base_window"), dict) else {}
    rolling_start = str(base_window.get("start") or "").split("T", 1)[0]
    incremental = source_meta.get("incremental_window", {}) if isinstance(source_meta.get("incremental_window"), dict) else {}
    rolling_end = str((incremental.get("end") if isinstance(incremental, dict) else "") or "").split("T", 1)[0]
    if not rolling_start:
        rolling_start = str(pointer.get("current_rolling_window", {}).get("start") or "")
    if not rolling_end:
        rolling_end = str(pointer.get("current_rolling_window", {}).get("end") or "")
    pointer.update(
        {
            "last_updated": dt.datetime.now(TZ).isoformat(timespec="seconds"),
            "source_json": str(source_json),
            "source_markdown": source_markdown,
            "source_feishu_base_url": FIXED_TABLE_URL,
            "source_feishu_table_id": FIXED_TABLE_ID,
            "fixed_master_base_url": FIXED_TABLE_URL,
            "fixed_master_base_token": FIXED_BASE_TOKEN,
            "fixed_master_table_id": FIXED_TABLE_ID,
            "fixed_master_append_meta": append_meta.get("meta_json", ""),
            "canonical_output_fields": KEEP_FIELDS,
            "blank_fields": ["评论", "备注"],
            "rules_doc_path": str(RULES.path) if RULES is not None else "",
            "daily_rule": (
                "Run daily at 08:00 Asia/Shanghai. First read rules_doc_path, then read the fixed Feishu master table and build a dynamic no-reply profile from rows whose 状态 is 不需要回; "
                "use that profile to filter exact/no-reply-like Xiaohongshu candidates before selection. Then crawl the incremental window from yesterday 00:00 to the run time, "
                "aim for 25-50 high-quality new rows per day after relevance filtering by expanding to additional backend/deploy/database/config-friction keywords when needed, "
                "write local rolling 7-day Markdown/JSON outputs without body/comment-example fields, and use lark-cli to append only new Xiaohongshu links "
                "to the fixed Feishu master table. Do not lower the quality bar or duplicate existing links just to reach 25 rows. Do not create a new Feishu Base or table unless the user explicitly asks."
            ),
            "lead_selection_rule": (
                "目标帖子像一个正在做项目的人遇到了后端、数据库、登录权限、API Key、部署、环境变量或数据保存问题，"
                "或者像一个会做项目的人明确吐槽手动配置这些后端能力太麻烦；不要抓内容号在教小白认识 AI 编程工具的帖子。"
            ),
        }
    )
    if rolling_start and rolling_end:
        pointer["current_rolling_window"] = {"start": rolling_start, "end": rolling_end}
    POINTER_JSON.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Append Xiaohongshu InsForge rows to the fixed Feishu master Base table.")
    parser.add_argument("--source-json", type=Path, help="Local JSON produced by the daily XHS crawl. Defaults to source_json in the pointer.")
    parser.add_argument("--dry-run", action="store_true", help="Read source and fixed table, but do not write records or update pointer.")
    parser.add_argument("--no-update-pointer", action="store_true", help="Do not update outputs/xhs_insforge_master_pointer.json after a successful append.")
    args = parser.parse_args()

    pointer = load_pointer()
    configure_fixed_master(pointer)
    source_json = args.source_json or source_from_pointer(pointer)
    if not source_json.is_absolute():
        source_json = ROOT / source_json

    run_tag = dt.datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    source_rows, source_meta = load_source_rows(source_json)
    fixed_field_names = fixed_table_field_names()
    write_fields, missing_optional_fields = resolve_write_fields(fixed_field_names)
    existing_keys, existing_count_before, existing_pages = existing_note_keys()
    pending_rows, duplicate_count = unique_new_rows(source_rows, existing_keys, write_fields)
    rows_before_append_limit = len(pending_rows)
    rows_skipped_by_append_limit = max(0, rows_before_append_limit - APPEND_LIMIT)
    if rows_skipped_by_append_limit:
        pending_rows = pending_rows[:APPEND_LIMIT]
    payload_path = write_payload(pending_rows, run_tag, write_fields)

    uploaded = 0
    chunk_paths: list[str] = []
    if pending_rows and not args.dry_run:
        uploaded, chunk_paths = batch_append(pending_rows, run_tag, write_fields)

    existing_count_after = existing_count_before
    if not args.dry_run:
        _, existing_count_after, _ = existing_note_keys()

    meta = {
        "finished_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "dry_run": bool(args.dry_run),
        "fixed_master_url": FIXED_TABLE_URL,
        "base_token": FIXED_BASE_TOKEN,
        "table_id": FIXED_TABLE_ID,
        "source_fields": KEEP_FIELDS,
        "write_fields": write_fields,
        "fixed_table_fields": fixed_field_names,
        "missing_optional_fields": missing_optional_fields,
        "source_json": str(source_json.resolve()),
        "source_rows": len(source_rows),
        "existing_records_before": existing_count_before,
        "duplicates_skipped": duplicate_count,
        "append_min": APPEND_MIN,
        "append_limit": APPEND_LIMIT,
        "rules_doc": RULES.as_meta() if RULES is not None else {},
        "append_min_target_met": len(pending_rows) >= APPEND_MIN,
        "append_min_warning": ""
        if len(pending_rows) >= APPEND_MIN
        else "fewer than 25 unique new rows available after dedupe/final exclusion; crawler should expand keywords, but append script will not duplicate existing rows or lower quality.",
        "rows_before_append_limit": rows_before_append_limit,
        "rows_skipped_by_append_limit": rows_skipped_by_append_limit,
        "rows_to_append": len(pending_rows),
        "rows_uploaded": uploaded,
        "existing_records_after": existing_count_after,
        "payload_json": str(payload_path),
        "chunk_paths": chunk_paths,
        "existing_pages": existing_pages,
    }
    meta_json = OUT_DIR / f"lark_fixed_master_append_{run_tag}_meta.json"
    meta["meta_json"] = str(meta_json)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run and not args.no_update_pointer:
        update_pointer(pointer, source_json, source_meta, meta)

    print(json.dumps({"status": "dry_run" if args.dry_run else "complete", **meta}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
