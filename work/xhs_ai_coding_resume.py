import importlib.util
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
CURATE_SCRIPT = ROOT / "work" / "xhs_ai_coding_curate_and_collect.py"

spec = importlib.util.spec_from_file_location("curate", CURATE_SCRIPT)
curate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(curate)


RESUME_KEYWORDS = [
    "Cursor 小白",
    "Cursor 后端",
    "Cursor 数据库",
    "Cursor Supabase",
    "Cursor 做APP",
    "Cursor 做网站 后端",
    "AI 做APP 后端",
    "AI 做网站 后端",
    "AI 做产品 后端",
    "AI 搭建网站 数据库",
    "AI Agent 后端",
    "AI Agent 数据库",
    "AI Agent MCP",
    "Agent 开发 后端",
    "Agent 开发 数据库",
    "MCP 后端",
    "MCP 数据库",
    "Supabase AI 编程",
    "Supabase Vibe Coding",
    "Supabase Cursor",
    "Supabase 新手",
    "Supabase 小白",
    "Supabase 踩坑",
    "Supabase RLS 坑",
    "前端 操作数据库 安全",
    "AI 编程 API Key",
    "独立开发 AI Coding",
    "独立开发 Vibe Coding",
    "独立开发 Cursor",
    "独立开发 Supabase",
    "零基础 Vibe Coding",
    "零基础 AI 做APP",
    "零基础 AI 编程 后端",
    "新手 Cursor 项目",
    "新手 Supabase 后端",
    "小白 Supabase 后端",
    "小白 做APP 数据库",
    "小白 后端 数据库",
    "后端 数据库 AI 编程",
    "AI 项目 数据库",
    "AI 项目 后端",
    "MVP AI Coding 后端",
    "MVP 数据库 Supabase",
]


def run_search_treekill(keyword: str, variant: dict, timeout_s: int = 75):
    cmd = [
        "python",
        "-m",
        "scripts",
        "search",
        keyword,
        "--limit",
        "50",
        "--headless",
        "true",
    ]
    if variant.get("sort_by"):
        cmd.extend(["--sort-by", variant["sort_by"]])
    if variant.get("publish_time"):
        cmd.extend(["--publish-time", variant["publish_time"]])

    proc = subprocess.Popen(
        cmd,
        cwd=curate.SKILL_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        stdout, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        raise TimeoutError(f"search timed out after {timeout_s}s")
    raw = stdout.decode("utf-8", errors="replace")
    data = curate.extract_json(raw)
    if not data:
        raise ValueError("No JSON result")
    return data.get("results", []) or []


def main():
    records = curate.load_raw_records()
    print(
        json.dumps(
            {
                "start_filtered": len(records),
                "start_one_week": sum(1 for r in records.values() if r["is_one_week"]),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    failures = []
    variants = [
        {"sort_by": None, "publish_time": None},
        {"sort_by": "最新", "publish_time": "半年内"},
        {"sort_by": "最多收藏", "publish_time": "半年内"},
    ]
    curate.RAW_OUT.mkdir(parents=True, exist_ok=True)

    for variant_index, variant in enumerate(variants, start=1):
        print(f"resume_variant={variant_index} count={len(records)} {variant}", flush=True)
        for index, keyword in enumerate(RESUME_KEYWORDS, start=1):
            if len(records) >= curate.TARGET:
                rows, window = curate.select_rows(records)
                curate.write_outputs(rows, window, failures, records)
                return
            print(f"[{index}/{len(RESUME_KEYWORDS)}] {keyword}", flush=True)
            try:
                items = run_search_treekill(keyword, variant)
            except Exception as exc:
                failures.append(
                    {
                        "keyword": keyword,
                        "variant": variant,
                        "error": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                time.sleep(3)
                continue

            raw_path = curate.RAW_OUT / f"resume_v{variant_index}_{curate.safe_name(keyword)}.json"
            raw_path.write_text(
                json.dumps({"keyword": keyword, "variant": variant, "results": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            for item in items:
                curate.add_item(records, item, keyword, str(raw_path))
            print(
                f"filtered_count={len(records)} one_week={sum(1 for r in records.values() if r['is_one_week'])}",
                flush=True,
            )
            time.sleep(4 if index % 4 else 12)

    rows, window = curate.select_rows(records)
    curate.write_outputs(rows, window, failures, records)


if __name__ == "__main__":
    main()
