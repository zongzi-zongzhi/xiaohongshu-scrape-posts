import csv
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
OUTPUT_DIR = ROOT / "outputs"
RAW_DIR = ROOT / "work" / "xhs_recent_cli_raw"
INBOX_MD = Path(r"D:\czj note\00_Inbox\xhs_insforge_pain_posts_100_table.md")
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
TARGET = 100

KEYWORDS = [
    "Supabase 坑",
    "Supabase 劝退",
    "Supabase 翻车",
    "Supabase 后端",
    "Supabase 数据库",
    "Supabase RLS",
    "Supabase 安全",
    "Supabase 部署",
    "Supabase 替代",
    "Firebase 替代",
    "后端开发 痛点",
    "后端 崩溃",
    "后端 开发 坑",
    "后端 太难了",
    "后端 现状",
    "前端 操作数据库 安全",
    "前端 后端 数据库",
    "数据库 崩溃",
    "数据库 连接 问题",
    "数据库 设计 坑",
    "数据库 新手",
    "数据库 部署",
    "独立开发 后端",
    "独立开发 数据库",
    "独立开发 技术栈",
    "独立开发 SaaS",
    "独立开发 踩坑",
    "程序员 独立开发 坑",
    "AI 编程 后端",
    "AI coding 后端",
    "vibe coding 坑",
    "Cursor 后端 数据库",
    "MCP 后端",
    "API 密钥 泄露",
    "全栈 项目 技术选型",
    "自建后端 坑",
    "服务器 部署 坑",
]

PAIN_TERMS = [
    "坑",
    "劝退",
    "翻车",
    "崩溃",
    "危险",
    "安全",
    "泄露",
    "痛点",
    "现状",
    "太难",
    "问题",
    "新手",
    "注意",
    "成本",
    "穷鬼",
    "选型",
    "怎么选",
    "替代",
    "不要",
    "必看",
    "闭环",
]

TOPIC_TERMS = [
    "supabase",
    "firebase",
    "后端",
    "数据库",
    "独立开发",
    "saas",
    "api",
    "密钥",
    "agent",
    "cursor",
    "vibe",
    "mcp",
]


def extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON object found")


def note_time(note_id: str) -> datetime | None:
    if not re.match(r"^[0-9a-f]{24}$", note_id or ""):
        return None
    try:
        return datetime.fromtimestamp(int(note_id[:8], 16), tz=TZ)
    except Exception:
        return None


def to_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().lower().replace(",", "")
    if not text:
        return 0
    multiplier = 1
    if text.endswith(("w", "万")):
        multiplier = 10000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else 0


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def repair_text(value: Any) -> str:
    text = "" if value is None else str(value)
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        return text
    if cjk_count(repaired) > cjk_count(text):
        return repaired
    return text


def esc_md(value: Any) -> str:
    return repair_text(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def safe_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value).strip("_")


def make_url(note_id: str, token: str) -> str:
    return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search"


def run_search(keyword: str, variant: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    cmd = [
        "python",
        "-m",
        "scripts",
        "search",
        keyword,
        "--limit",
        str(limit),
        "--headless",
        "true",
    ]
    if variant.get("sort_by"):
        cmd.extend(["--sort-by", variant["sort_by"]])
    if variant.get("publish_time"):
        cmd.extend(["--publish-time", variant["publish_time"]])

    proc = subprocess.run(
        cmd,
        cwd=SKILL_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=95,
    )
    raw = proc.stdout.decode("utf-8", errors="replace")
    data = extract_json(raw)
    return data.get("results", []) or []


def add_item(
    records: dict[str, dict[str, Any]],
    item: dict[str, Any],
    keyword: str,
    variant: dict[str, Any],
    cutoff: datetime,
) -> None:
    note_id = str(item.get("id") or "").strip()
    published_at = note_time(note_id)
    if not published_at or published_at < cutoff:
        return

    title = repair_text(item.get("title", "")).strip()
    author = repair_text(item.get("user", "")).strip()
    token = str(item.get("xsec_token") or "").strip()
    if not note_id or not title or not author or not token or "#" in note_id:
        return

    if note_id not in records:
        records[note_id] = {
            "note_id": note_id,
            "title": title,
            "url": make_url(note_id, token),
            "liked_count": to_int(item.get("liked_count")),
            "comment_count": to_int(item.get("comment_count")),
            "collected_count": to_int(item.get("collected_count")),
            "shared_count": to_int(item.get("shared_count")),
            "author": author,
            "author_id": item.get("user_id", ""),
            "published_at": published_at.isoformat(),
            "matched_keywords": [keyword],
            "variants": [variant],
        }
    else:
        records[note_id]["matched_keywords"].append(keyword)
        records[note_id]["variants"].append(variant)


def collect_stage(
    cutoff: datetime,
    variants: list[dict[str, Any]],
    records: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    records = dict(records or {})
    failures = []
    for variant_index, variant in enumerate(variants, start=1):
        before = len(records)
        print(
            f"variant {variant_index}/{len(variants)} cutoff={cutoff.isoformat()} "
            f"sort={variant.get('sort_by')} time={variant.get('publish_time')}",
            flush=True,
        )
        for keyword_index, keyword in enumerate(KEYWORDS, start=1):
            print(f"[{keyword_index}/{len(KEYWORDS)}] {keyword}", flush=True)
            try:
                items = run_search(keyword, variant)
            except Exception as exc:
                failures.append(
                    {
                        "keyword": keyword,
                        "variant": variant,
                        "error": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                time.sleep(5)
                continue

            raw_path = RAW_DIR / f"v{variant_index}_{safe_name(keyword)}.json"
            raw_path.write_text(
                json.dumps({"keyword": keyword, "variant": variant, "results": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            for item in items:
                add_item(records, item, keyword, variant, cutoff)

            print(f"recent_count={len(records)}", flush=True)
            if len(records) >= TARGET:
                break
            time.sleep(4 if keyword_index % 4 else 12)
        print(f"variant_added={len(records) - before}", flush=True)
        if len(records) >= TARGET:
            break
        time.sleep(12)
    return records, failures


def score_record(record: dict[str, Any]) -> int:
    haystack = f"{record.get('title', '')} {' '.join(record.get('matched_keywords', []))}".lower()
    score = 0
    for term in PAIN_TERMS:
        if term.lower() in haystack:
            score += 3
    for term in TOPIC_TERMS:
        if term.lower() in haystack:
            score += 2
    return score


def select_rows(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in records.values():
        item = dict(row)
        item["matched_keywords"] = "、".join(dict.fromkeys(item.get("matched_keywords", [])))
        item["pain_score"] = score_record(row)
        item["engagement_score"] = (
            item["liked_count"]
            + item["collected_count"]
            + item["comment_count"] * 2
            + item["shared_count"] * 2
        )
        rows.append(item)
    rows.sort(
        key=lambda item: (
            item["pain_score"],
            item["comment_count"],
            item["engagement_score"],
            item["published_at"],
        ),
        reverse=True,
    )
    return rows[:TARGET]


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    json_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100_recent.json"
    csv_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100_recent.csv"
    md_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100_table.md"

    json_path.write_text(json.dumps({"meta": meta, "posts": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = [
        "title",
        "url",
        "liked_count",
        "comment_count",
        "collected_count",
        "published_at",
        "author",
        "matched_keywords",
        "note_id",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

    lines = [
        "| 帖子标题 | 帖子链接 | 点赞 | 评论 | 收藏 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {esc_md(row['title'])} | [打开]({row['url']}) | "
            f"{row['liked_count']} | {row['comment_count']} | {row['collected_count']} |"
        )
    content = "\n".join(lines) + "\n"
    md_path.write_text(content, encoding="utf-8-sig")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(content, encoding="utf-8-sig")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "workspace_md": str(md_path),
                "inbox_md": str(INBOX_MD),
                "json": str(json_path),
                "csv": str(csv_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    one_week_cutoff = NOW - timedelta(days=7)
    two_week_cutoff = NOW - timedelta(days=14)
    print(f"now={NOW.isoformat()}", flush=True)
    print(f"one_week_cutoff={one_week_cutoff.isoformat()}", flush=True)
    print(f"two_week_cutoff={two_week_cutoff.isoformat()}", flush=True)

    one_week_variants = [
        {"sort_by": None, "publish_time": None},
        {"sort_by": "最新", "publish_time": "一周内"},
        {"sort_by": "最多评论", "publish_time": "一周内"},
        {"sort_by": "最多收藏", "publish_time": "一周内"},
    ]
    two_week_variants = [
        {"sort_by": None, "publish_time": None},
        {"sort_by": "最新", "publish_time": "半年内"},
        {"sort_by": "最多评论", "publish_time": "半年内"},
        {"sort_by": "最多收藏", "publish_time": "半年内"},
        {"sort_by": "最多点赞", "publish_time": "半年内"},
    ]

    one_week_records, failures = collect_stage(one_week_cutoff, one_week_variants)
    final_records = one_week_records
    selection_window = "7_days"

    if len(one_week_records) < TARGET:
        print(f"one_week_not_enough={len(one_week_records)}; expanding_to_14_days", flush=True)
        final_records, more_failures = collect_stage(two_week_cutoff, two_week_variants, records=one_week_records)
        failures.extend(more_failures)
        selection_window = "14_days" if len(final_records) >= TARGET else "14_days_partial"
    else:
        print(f"one_week_enough={len(one_week_records)}", flush=True)

    rows = select_rows(final_records)
    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "now": NOW.isoformat(),
        "selection_window": selection_window,
        "one_week_cutoff": one_week_cutoff.isoformat(),
        "two_week_cutoff": two_week_cutoff.isoformat(),
        "one_week_candidate_count": len(one_week_records),
        "final_candidate_count": len(final_records),
        "selected_count": len(rows),
        "failures": failures,
        "keywords": KEYWORDS,
        "note": "Only public search data was read. No like/comment/favorite/message/publish actions were performed.",
    }
    write_outputs(rows, meta)


if __name__ == "__main__":
    main()
