from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
BASE_TOKEN = "NMfdbS7I7aPeMDsdhdUcuXRAnxb"
TABLE_ID = "tblq1XSI6BGBugyN"
VIEW_ID = "vewgQbhR3M"
PAYLOAD_JSON = ROOT / "work" / "xhs_minimal_full_body_records_payload.json"
META_JSON = ROOT / "outputs" / "lark_base_xhs_minimal_full_body_update_meta.json"

KEEP_FIELDS = ["发布时间", "帖子名字", "帖子链接", "匹配关键词", "评论例子", "帖子正文部分"]
DROP_FIELDS = ["评论方向", "帖主昵称", "粉丝数", "联系方式", "来源"]
BATCH_SLEEP = 0.12


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


def run_lark(args: list[str], *, retries: int = 0, yes: bool = False) -> dict[str, Any]:
    cmd = ["lark-cli.cmd", *args, "--as", "user", "--format", "json"]
    if yes:
        cmd.append("--yes")
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
        if proc.returncode == 0:
            return parse_json(proc.stdout)
        merged = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if "1254291" in merged and attempt < retries:
            time.sleep(1.5 + attempt)
            continue
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    raise AssertionError("unreachable")


def field_names(fields_response: dict[str, Any]) -> list[str]:
    return [field["name"] for field in fields_response.get("data", {}).get("fields", [])]


def field_id_by_name(fields_response: dict[str, Any]) -> dict[str, str]:
    return {
        field["name"]: field["id"]
        for field in fields_response.get("data", {}).get("fields", [])
        if isinstance(field, dict) and field.get("name") and field.get("id")
    }


def load_payload() -> tuple[list[str], list[list[Any]]]:
    payload = json.loads(PAYLOAD_JSON.read_text(encoding="utf-8"))
    fields = payload["fields"]
    rows = payload["rows"]
    if fields != KEEP_FIELDS:
        raise RuntimeError(f"payload fields do not match KEEP_FIELDS: {fields}")
    if len(rows) != 100:
        raise RuntimeError(f"expected 100 rows, got {len(rows)}")
    empty_body = sum(1 for row in rows if not str(row[-1] or "").strip())
    if empty_body:
        raise RuntimeError(f"payload still has empty body rows: {empty_body}")
    return fields, rows


def current_record_maps() -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    records = run_lark(
        [
            "base",
            "+record-list",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            TABLE_ID,
            "--limit",
            "200",
        ],
        retries=1,
    )
    data = records.get("data", {})
    fields = data.get("fields", [])
    row_data = data.get("data", [])
    record_ids = data.get("record_id_list", [])
    if not isinstance(fields, list) or not isinstance(row_data, list) or not isinstance(record_ids, list):
        raise RuntimeError(f"unexpected record-list shape: {records}")
    if "帖子链接" not in fields:
        raise RuntimeError(f"current table lacks 帖子链接 field: {fields}")
    url_index = fields.index("帖子链接")
    title_index = fields.index("帖子名字") if "帖子名字" in fields else -1
    by_url: dict[str, str] = {}
    by_title: dict[str, str] = {}
    duplicate_titles: set[str] = set()
    for row, record_id in zip(row_data, record_ids):
        if isinstance(row, list) and url_index < len(row):
            url = str(row[url_index] or "").strip()
            if url and isinstance(record_id, str):
                by_url[url] = record_id
        if isinstance(row, list) and title_index >= 0 and title_index < len(row):
            title = str(row[title_index] or "").strip()
            if title and isinstance(record_id, str):
                if title in by_title and by_title[title] != record_id:
                    duplicate_titles.add(title)
                by_title[title] = record_id
    for title in duplicate_titles:
        by_title.pop(title, None)
    return by_url, by_title, records


def write_record_payload(index: int, row_map: dict[str, Any]) -> Path:
    path = ROOT / "work" / f"xhs_minimal_record_update_{index:03d}.json"
    path.write_text(json.dumps(row_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def update_records(fields: list[str], rows: list[list[Any]], record_by_url: dict[str, str], record_by_title: dict[str, str]) -> dict[str, Any]:
    url_index = fields.index("帖子链接")
    title_index = fields.index("帖子名字")
    updated = 0
    missing_urls: list[str] = []
    matched_by_title = 0
    for index, row in enumerate(rows, start=1):
        row_map = {field: row[field_index] if field_index < len(row) else "" for field_index, field in enumerate(fields)}
        url = str(row[url_index] or "").strip()
        title = str(row[title_index] or "").strip()
        record_id = record_by_url.get(url)
        if not record_id and title:
            record_id = record_by_title.get(title)
            if record_id:
                matched_by_title += 1
        if not record_id:
            missing_urls.append(url)
            continue
        payload_path = write_record_payload(index, row_map)
        run_lark(
            [
                "base",
                "+record-upsert",
                "--base-token",
                BASE_TOKEN,
                "--table-id",
                TABLE_ID,
                "--record-id",
                record_id,
                "--json",
                f"@{payload_path.relative_to(ROOT).as_posix()}",
            ],
            retries=2,
        )
        updated += 1
        if updated % 10 == 0 or updated == len(rows):
            print(json.dumps({"updated": updated, "total": len(rows)}, ensure_ascii=False), flush=True)
        time.sleep(BATCH_SLEEP)

    return {"updated": updated, "matched_by_title": matched_by_title, "missing_urls": missing_urls}


def delete_extra_fields(field_ids: dict[str, str]) -> list[dict[str, Any]]:
    deleted: list[dict[str, Any]] = []
    for name in DROP_FIELDS:
        field_id = field_ids.get(name)
        if not field_id:
            deleted.append({"name": name, "status": "not_found"})
            continue
        result = run_lark(
            [
                "base",
                "+field-delete",
                "--base-token",
                BASE_TOKEN,
                "--table-id",
                TABLE_ID,
                "--field-id",
                field_id,
            ],
            yes=True,
            retries=1,
        )
        deleted.append({"name": name, "field_id": field_id, "status": "deleted", "response": result})
        time.sleep(0.2)
    return deleted


def set_visible_fields() -> dict[str, Any]:
    path = ROOT / "work" / "lark_visible_fields_xhs_minimal_full_body.json"
    path.write_text(json.dumps({"visible_fields": KEEP_FIELDS}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return run_lark(
        [
            "base",
            "+view-set-visible-fields",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            TABLE_ID,
            "--view-id",
            VIEW_ID,
            "--json",
            f"@{path.relative_to(ROOT).as_posix()}",
        ],
        retries=1,
    )


def main() -> None:
    fields, rows = load_payload()
    before_fields = run_lark(["base", "+field-list", "--base-token", BASE_TOKEN, "--table-id", TABLE_ID])
    before_field_names = field_names(before_fields)
    missing_keep = [name for name in KEEP_FIELDS if name not in before_field_names]
    if missing_keep:
        raise RuntimeError(f"current table missing keep fields: {missing_keep}")

    record_by_url, record_by_title, before_records = current_record_maps()
    update_result = update_records(fields, rows, record_by_url, record_by_title)
    if update_result["missing_urls"]:
        raise RuntimeError(f"some payload rows could not match existing records: {update_result['missing_urls'][:5]}")

    delete_result = delete_extra_fields(field_id_by_name(before_fields))
    visible_result = set_visible_fields()
    after_fields = run_lark(["base", "+field-list", "--base-token", BASE_TOKEN, "--table-id", TABLE_ID])
    after_records = run_lark(
        ["base", "+record-list", "--base-token", BASE_TOKEN, "--table-id", TABLE_ID, "--limit", "200"],
        retries=1,
    )

    after_data = after_records.get("data", {})
    after_row_data = after_data.get("data", [])
    after_record_count = len(after_data.get("record_id_list", []))
    after_fields_list = after_data.get("fields", [])
    body_index = after_fields_list.index("帖子正文部分") if "帖子正文部分" in after_fields_list else -1
    empty_body = 0
    if body_index >= 0:
        empty_body = sum(
            1
            for row in after_row_data
            if isinstance(row, list) and (body_index >= len(row) or not str(row[body_index] or "").strip())
        )

    meta = {
        "base_token": BASE_TOKEN,
        "table_id": TABLE_ID,
        "url": f"https://zcnvjlr35o2b.feishu.cn/base/{BASE_TOKEN}?table={TABLE_ID}",
        "payload": str(PAYLOAD_JSON),
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "keep_fields": KEEP_FIELDS,
        "drop_fields": DROP_FIELDS,
        "before_field_names": before_field_names,
        "before_record_count": len(before_records.get("data", {}).get("record_id_list", [])),
        "update_result": update_result,
        "delete_result": delete_result,
        "visible_result": visible_result,
        "after_field_names": field_names(after_fields),
        "after_record_count": after_record_count,
        "after_empty_body": empty_body,
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
