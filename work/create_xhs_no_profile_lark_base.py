from __future__ import annotations

import argparse
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
IN_JSON = ROOT / "outputs" / "xhs_insforge_expanded_leads_comments_7day_20260721_20260727.json"
OUT_JSON = ROOT / "outputs" / "xhs_insforge_expanded_leads_comments_7day_no_profile_20260721_20260727.json"
OUT_MD = ROOT / "outputs" / "xhs_insforge_expanded_leads_comments_7day_no_profile_20260721_20260727.md"
D_MD = Path(r"D:\czj note\00_Inbox\小红书建联线索池_评论方向_扩展口径_删主页链接_20260721-20260727.md")
FIELDS_JSON = ROOT / "work" / "xhs_no_profile_base_fields.json"
RECORDS_JSON = ROOT / "work" / "xhs_no_profile_records_payload.json"
PUBLIC_PERMISSION_JSON = ROOT / "work" / "base_public_permission_no_profile.json"
META_JSON = ROOT / "outputs" / "lark_base_xhs_no_profile_20260721_20260727_upload_meta.json"

BASE_NAME = "小红书 InsForge 建联线索池 删主页链接 20260721-20260727"
TABLE_NAME = "线索池"
BATCH_SIZE = 50
DROP_FIELDS = {"帖主主页链接"}
FIELDS = [
    "发布时间",
    "帖子名字",
    "帖子链接",
    "匹配关键词",
    "评论方向",
    "评论例子",
    "帖主昵称",
    "粉丝数",
    "联系方式",
    "帖子正文部分",
    "来源",
]


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


def run_lark(args: list[str], *, retries: int = 0, yes: bool = False) -> tuple[dict[str, Any], str, str]:
    cmd = ["lark-cli.cmd", *args, "--as", "user", "--format", "json"]
    if yes:
        cmd.append("--yes")
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
        if proc.returncode == 0:
            return parse_json(proc.stdout), proc.stdout, proc.stderr
        merged = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if "1254291" in merged and attempt < retries:
            time.sleep(2 + attempt)
            continue
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def find_token(obj: dict[str, Any]) -> str:
    values: list[str] = []
    for node in walk(obj):
        for key in ("base_token", "app_token", "token"):
            value = node.get(key)
            if isinstance(value, str) and value:
                values.append(value)
    for value in values:
        if value.startswith(("basc", "base", "app")):
            return value
    return values[0] if values else ""


def find_table_id(obj: dict[str, Any]) -> str:
    for node in walk(obj):
        for key in ("table_id", "id"):
            value = node.get(key)
            if isinstance(value, str) and value.startswith("tbl"):
                return value
    return ""


def item_count(obj: dict[str, Any]) -> int | None:
    for node in walk(obj):
        items = node.get("items")
        if isinstance(items, list):
            return len(items)
        records = node.get("records")
        if isinstance(records, list):
            return len(records)
    return None


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def build_markdown(rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(FIELDS) + " |"
    sep = "| " + " | ".join(["---"] * len(FIELDS)) + " |"
    lines = ["# 小红书建联线索池（删主页链接版）", "", header, sep]
    for row in rows:
        lines.append("| " + " | ".join(markdown_escape(row.get(field, "")) for field in FIELDS) + " |")
    return "\n".join(lines) + "\n"


def prepare_files() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = json.loads(IN_JSON.read_text(encoding="utf-8"))
    source_rows = source.get("rows", source if isinstance(source, list) else [])
    if not isinstance(source_rows, list):
        raise RuntimeError("input rows are not a list")

    rows: list[dict[str, Any]] = []
    for source_row in source_rows:
        if not isinstance(source_row, dict):
            continue
        rows.append({field: source_row.get(field, "") for field in FIELDS})

    if not rows:
        raise RuntimeError("no rows to export")

    meta = {
        "source": str(IN_JSON),
        "drop_fields": sorted(DROP_FIELDS),
        "fields": FIELDS,
        "rows_total": len(rows),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    OUT_JSON.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = build_markdown(rows)
    OUT_MD.write_text(markdown, encoding="utf-8")
    D_MD.parent.mkdir(parents=True, exist_ok=True)
    D_MD.write_text(markdown, encoding="utf-8")

    field_defs = [{"name": field, "type": "text"} for field in FIELDS]
    FIELDS_JSON.write_text(json.dumps(field_defs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    records_payload = {"fields": FIELDS, "rows": [[row.get(field, "") for field in FIELDS] for row in rows]}
    RECORDS_JSON.write_text(json.dumps(records_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return rows, records_payload


def create_and_upload(records_payload: dict[str, Any], *, set_public_read: bool) -> dict[str, Any]:
    created, _, _ = run_lark(
        [
            "base",
            "+base-create",
            "--name",
            BASE_NAME,
            "--time-zone",
            "Asia/Shanghai",
            "--table-name",
            TABLE_NAME,
            "--fields",
            f"@{FIELDS_JSON.relative_to(ROOT).as_posix()}",
        ]
    )
    base_token = find_token(created)
    if not base_token:
        raise RuntimeError(f"could not find base token: {created}")

    table_list, _, _ = run_lark(["base", "+table-list", "--base-token", base_token])
    table_id = find_table_id(table_list) or find_table_id(created)
    if not table_id:
        raise RuntimeError(f"could not find table id: {table_list}")

    fields_response, _, _ = run_lark(["base", "+field-list", "--base-token", base_token, "--table-id", table_id])

    uploaded = 0
    temp_payloads: list[str] = []
    rows = records_payload["rows"]
    for start in range(0, len(rows), BATCH_SIZE):
        chunk = rows[start : start + BATCH_SIZE]
        payload_path = ROOT / "work" / f"xhs_no_profile_records_payload_{start:03d}.json"
        payload_path.write_text(
            json.dumps({"fields": records_payload["fields"], "rows": chunk}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temp_payloads.append(str(payload_path))
        run_lark(
            [
                "base",
                "+record-batch-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                f"@{payload_path.relative_to(ROOT).as_posix()}",
            ],
            retries=2,
        )
        uploaded += len(chunk)
        print(json.dumps({"uploaded": uploaded, "total": len(rows)}, ensure_ascii=False), flush=True)
        time.sleep(0.35)

    permission_patch: dict[str, Any] | None = None
    if set_public_read:
        PUBLIC_PERMISSION_JSON.write_text(
            json.dumps({"external_access": True, "link_share_entity": "anyone_readable"}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        permission_patch, _, _ = run_lark(
            [
                "drive",
                "permission.public",
                "patch",
                "--token",
                base_token,
                "--type",
                "bitable",
                "--data",
                f"@{PUBLIC_PERMISSION_JSON.relative_to(ROOT).as_posix()}",
            ],
            yes=True,
        )

    permission_get, _, _ = run_lark(
        ["drive", "permission.public", "get", "--token", base_token, "--type", "bitable"],
        retries=1,
    )
    verify_records, _, _ = run_lark(
        ["base", "+record-list", "--base-token", base_token, "--table-id", table_id, "--limit", "200"],
        retries=1,
    )

    url = f"https://zcnvjlr35o2b.feishu.cn/base/{base_token}?table={table_id}"
    meta = {
        "base_name": BASE_NAME,
        "table_name": TABLE_NAME,
        "base_token": base_token,
        "table_id": table_id,
        "url": url,
        "input_json": str(IN_JSON),
        "output_json": str(OUT_JSON),
        "output_md": str(OUT_MD),
        "d_md": str(D_MD),
        "rows_total": len(rows),
        "rows_uploaded": uploaded,
        "verify_record_count": item_count(verify_records),
        "fields_response": fields_response,
        "permission_patch": permission_patch,
        "permission_get": permission_get,
        "temp_payloads": temp_payloads,
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--set-public-read", action="store_true")
    args = parser.parse_args()

    rows, records_payload = prepare_files()
    result: dict[str, Any] = {
        "rows_total": len(rows),
        "fields": FIELDS,
        "d_md": str(D_MD),
        "output_md": str(OUT_MD),
        "output_json": str(OUT_JSON),
        "records_payload": str(RECORDS_JSON),
        "fields_json": str(FIELDS_JSON),
    }
    if args.upload:
        result["lark"] = create_and_upload(records_payload, set_public_read=args.set_public_read)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
