from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
CURRENT_OUTPUTS = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-30\insforge-xhs-daily-crawl-handoff\outputs")
TZ = timezone(timedelta(hours=8))

OUT_JSON = OUT_DIR / "xhs_lark_history_bases_records_20260731.json"
RAW_JSON = WORK_DIR / "xhs_lark_history_bases_records_20260731_raw.json"


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


def meta_sources() -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    sources: list[dict[str, str]] = []
    for path in sorted(OUT_DIR.glob("lark_base_xhs*.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        base_token = str(meta.get("base_token") or "").strip()
        table_id = str(meta.get("table_id") or "").strip()
        if not base_token or not table_id:
            continue
        key = (base_token, table_id)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "meta_file": path.name,
                "base_name": str(meta.get("base_name") or ""),
                "base_token": base_token,
                "table_id": table_id,
                "url": str(meta.get("url") or f"https://zcnvjlr35o2b.feishu.cn/base/{base_token}?table={table_id}"),
                "source_json": str(meta.get("source_json") or ""),
            }
        )
    return sources


def pull_table(source: dict[str, str]) -> dict[str, Any]:
    offset = 0
    raw_pages: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    field_order: list[str] = []
    while True:
        result = run_lark(
            [
                "base",
                "+record-list",
                "--base-token",
                source["base_token"],
                "--table-id",
                source["table_id"],
                "--limit",
                "200",
                "--offset",
                str(offset),
            ],
            retries=2,
        )
        data = result.get("data", {}) if isinstance(result, dict) else {}
        fields = data.get("fields") or []
        values = data.get("data") or []
        record_ids = data.get("record_id_list") or []
        has_more = bool(data.get("has_more"))
        if isinstance(fields, list) and fields:
            field_order = [str(field) for field in fields]
        for index, value_row in enumerate(values):
            if not isinstance(value_row, list):
                continue
            row = {field: value_row[i] if i < len(value_row) else "" for i, field in enumerate(field_order)}
            row["_lark_record_id"] = record_ids[index] if index < len(record_ids) else ""
            row["_lark_base_name"] = source.get("base_name", "")
            row["_lark_base_url"] = source.get("url", "")
            row["_lark_meta_file"] = source.get("meta_file", "")
            rows.append(row)
        raw_pages.append(
            {
                "offset": offset,
                "count": len(values),
                "has_more": has_more,
                "fields": field_order,
            }
        )
        if not has_more or not values:
            break
        offset += len(values)
    return {"source": source, "field_order": field_order, "pages": raw_pages, "rows": rows}


def main() -> int:
    sources = meta_sources()
    pulled: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        print(f"pull_lark_base [{index}/{len(sources)}] {source['base_token']} {source['table_id']} {source['base_name']}", flush=True)
        table = pull_table(source)
        pulled.append({key: table[key] for key in ("source", "field_order", "pages")})
        all_rows.extend(table["rows"])

    meta = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source_count": len(sources),
        "row_count": len(all_rows),
        "note": "Read-only pull of historical Xiaohongshu Feishu Base tables for cross-checking and backfilling local master data.",
        "sources": pulled,
    }
    payload = {"meta": meta, "rows": all_rows}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    RAW_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    CURRENT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (CURRENT_OUTPUTS / OUT_JSON.name).write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"status": "complete", "sources": len(sources), "rows": len(all_rows), "output_json": str(OUT_JSON)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
