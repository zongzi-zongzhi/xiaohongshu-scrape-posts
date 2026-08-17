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
RAW_OUT = ROOT / "work" / "xhs_ai_coding_raw"
INBOX_MD = Path(r"D:\czj note\00_Inbox\xhs_insforge_ai_coding_pain_posts_100_table.md")
WORKSPACE_MD = OUTPUT_DIR / "xhs_insforge_ai_coding_pain_posts_100_table.md"
JSON_OUT = OUTPUT_DIR / "xhs_insforge_ai_coding_pain_posts_100.json"
CSV_OUT = OUTPUT_DIR / "xhs_insforge_ai_coding_pain_posts_100.csv"

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
ONE_WEEK_CUTOFF = NOW - timedelta(days=7)
TWO_WEEK_CUTOFF = NOW - timedelta(days=14)
TARGET = 100

RAW_SOURCES = [
    ROOT / "work" / "xhs_recent_cli_raw",
    ROOT / "work" / "xhs_recent_raw",
    ROOT / "work" / "xhs_raw",
]

FOCUSED_KEYWORDS = [
    "小白AI Coding 踩坑",
    "AI Coding 踩坑",
    "AI 编程 踩坑",
    "AI Coding 小白",
    "AI 编程 小白",
    "Vibe Coding 踩坑",
    "Vibe Coding 小白",
    "vibecoding 踩坑",
    "vibe code 踩坑",
    "Vibe Coding 后端",
    "Vibe Coding 数据库",
    "Vibe Coding Supabase",
    "Vibe Coding API",
    "Cursor 踩坑",
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
    "API Key 泄露",
    "AI 编程 API Key",
    "密钥 泄露 独立开发",
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

EXCLUDE_RE = re.compile(
    r"(实习|实习生|招聘|招募|招人|招生|内推|校招|社招|秋招|春招|求职|简历|"
    r"面试|一面|二面|三面|终面|offer|Offer|OFFER|HC|hc|岗位|找工作|候选人|"
    r"面经|八股|上岸|薪资|薪水|工资|应届|大厂|小厂|不想再招|水平堪忧|一天面了|"
    r"面了\s*\d+|面\s*\d+\s*个|外包|裁员|跳槽)"
)

AI_TERMS = [
    "ai",
    "ai coding",
    "ai编程",
    "ai 编程",
    "vibe",
    "vibecoding",
    "cursor",
    "agent",
    "mcp",
    "claude code",
    "trae",
    "windsurf",
    "bolt",
    "lovable",
]

PAIN_TERMS = [
    "踩坑",
    "坑",
    "避坑",
    "翻车",
    "小白",
    "新手",
    "零基础",
    "不会",
    "搞不懂",
    "安全",
    "泄露",
    "报错",
    "闭环",
    "复盘",
    "怎么选",
    "选择",
    "连接",
    "部署",
]

BACKEND_TERMS = [
    "后端",
    "数据库",
    "supabase",
    "firebase",
    "postgres",
    "sql",
    "api",
    "api key",
    "密钥",
    "rls",
    "auth",
    "mcp",
    "全栈",
    "app",
    "网站",
    "mvp",
    "独立开发",
]


def extract_json(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def note_time(note_id: str) -> datetime | None:
    if not re.match(r"^[0-9a-f]{24}$", note_id or ""):
        return None
    try:
        return datetime.fromtimestamp(int(note_id[:8], 16), tz=TZ)
    except Exception:
        return None


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def repair_text(value: Any) -> str:
    text = "" if value is None else str(value)
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        return text
    return repaired if cjk_count(repaired) > cjk_count(text) else text


def to_int(value: Any) -> int:
    text = "" if value is None else str(value).strip().lower().replace(",", "")
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


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def relevance_score(title: str, keyword_text: str) -> int:
    haystack = f"{title} {keyword_text}".lower()
    if EXCLUDE_RE.search(title) or EXCLUDE_RE.search(keyword_text):
        return -999

    has_ai = contains_any(haystack, AI_TERMS)
    has_backend = contains_any(haystack, BACKEND_TERMS)
    has_pain = contains_any(haystack, PAIN_TERMS)
    has_supabase_pain = "supabase" in haystack and (has_backend or has_pain or has_ai)

    if not ((has_ai and (has_backend or has_pain)) or has_supabase_pain):
        return -999

    score = 0
    for term in AI_TERMS:
        if term.lower() in haystack:
            score += 5
    for term in PAIN_TERMS:
        if term.lower() in haystack:
            score += 4
    for term in BACKEND_TERMS:
        if term.lower() in haystack:
            score += 3
    if any(term in title for term in ["小白", "新手", "零基础"]):
        score += 8
    if any(term in title.lower() for term in ["vibe", "cursor", "ai coding", "agent"]):
        score += 6
    if any(term in title for term in ["踩坑", "避坑", "翻车"]):
        score += 6
    return score


def make_url(note_id: str, token: str) -> str:
    return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search"


def add_item(records: dict[str, dict[str, Any]], item: dict[str, Any], keyword: str, source: str) -> None:
    note_id = str(item.get("id") or "").strip()
    published_at = note_time(note_id)
    if not published_at or published_at < TWO_WEEK_CUTOFF:
        return

    title = repair_text(item.get("title", "")).strip()
    author = repair_text(item.get("user", "")).strip()
    token = str(item.get("xsec_token") or "").strip()
    if not title or not author or not token or "#" in note_id:
        return

    score = relevance_score(title, keyword)
    if score < 0:
        if note_id in records:
            records.pop(note_id, None)
        return

    existing = records.get(note_id)
    if existing:
        existing["matched_keywords"].append(keyword)
        existing["source_files"].append(source)
        existing["relevance_score"] = max(existing["relevance_score"], score)
        return

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
        "source_files": [source],
        "relevance_score": score,
        "is_one_week": published_at >= ONE_WEEK_CUTOFF,
    }


def load_raw_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for directory in RAW_SOURCES + [RAW_OUT]:
        if not directory.exists():
            continue
        for path in list(directory.glob("*.json")) + list(directory.glob("*.log")):
            text = path.read_text(encoding="utf-8", errors="replace")
            data = extract_json(text)
            if not data:
                continue
            keyword = data.get("keyword") or path.stem
            results = data.get("results", [])
            if not isinstance(results, list):
                continue
            for item in results:
                add_item(records, item, str(keyword), str(path))
    return records


def run_search(keyword: str, variant: dict[str, Any]) -> list[dict[str, Any]]:
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
    proc = subprocess.run(
        cmd,
        cwd=SKILL_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=95,
    )
    raw = proc.stdout.decode("utf-8", errors="replace")
    data = extract_json(raw)
    if not data:
        raise ValueError("No JSON result")
    return data.get("results", []) or []


def collect_more(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    variants = [
        {"sort_by": None, "publish_time": None},
        {"sort_by": "最新", "publish_time": "半年内"},
        {"sort_by": "最多收藏", "publish_time": "半年内"},
        {"sort_by": "最多评论", "publish_time": "半年内"},
    ]
    RAW_OUT.mkdir(parents=True, exist_ok=True)

    for variant_index, variant in enumerate(variants, start=1):
        print(f"variant={variant_index}/{len(variants)} count={len(records)} {variant}", flush=True)
        for index, keyword in enumerate(FOCUSED_KEYWORDS, start=1):
            if len(records) >= TARGET:
                return failures
            print(f"[{index}/{len(FOCUSED_KEYWORDS)}] {keyword}", flush=True)
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

            raw_path = RAW_OUT / f"v{variant_index}_{safe_name(keyword)}.json"
            raw_path.write_text(
                json.dumps({"keyword": keyword, "variant": variant, "results": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            for item in items:
                add_item(records, item, keyword, str(raw_path))
            print(f"filtered_count={len(records)} one_week={sum(1 for r in records.values() if r['is_one_week'])}", flush=True)
            time.sleep(4 if index % 4 else 12)
    return failures


def safe_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value).strip("_")


def select_rows(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    one_week = [r for r in records.values() if r["is_one_week"]]
    older = [r for r in records.values() if not r["is_one_week"]]
    sort_key = lambda r: (r["relevance_score"], r["comment_count"], r["liked_count"] + r["collected_count"], r["published_at"])
    one_week.sort(key=sort_key, reverse=True)
    older.sort(key=sort_key, reverse=True)
    if len(one_week) >= TARGET:
        selected = one_week[:TARGET]
        window = "7_days"
    else:
        selected = (one_week + older)[:TARGET]
        window = "14_days" if len(selected) >= TARGET else "14_days_partial"
    return selected, window


def esc_md(value: Any) -> str:
    return repair_text(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def write_outputs(rows: list[dict[str, Any]], window: str, failures: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "now": NOW.isoformat(),
        "selection_window": window,
        "one_week_cutoff": ONE_WEEK_CUTOFF.isoformat(),
        "two_week_cutoff": TWO_WEEK_CUTOFF.isoformat(),
        "one_week_candidate_count": sum(1 for r in records.values() if r["is_one_week"]),
        "final_candidate_count": len(records),
        "selected_count": len(rows),
        "exclude_rule": EXCLUDE_RE.pattern,
        "focused_keywords": FOCUSED_KEYWORDS,
        "failures": failures,
        "note": "Curated for AI Coding/newbie/backend/database pain posts. Recruiting/internship/job-search/interview content was excluded. No interactions were performed.",
    }
    JSON_OUT.write_text(json.dumps({"meta": meta, "posts": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = ["title", "url", "liked_count", "comment_count", "collected_count", "published_at", "author", "matched_keywords", "note_id", "relevance_score"]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["matched_keywords"] = "、".join(dict.fromkeys(row.get("matched_keywords", [])))
            writer.writerow({field: out.get(field, "") for field in fields})

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
    WORKSPACE_MD.write_text(content, encoding="utf-8-sig")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(content, encoding="utf-8-sig")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "window": window,
                "workspace_md": str(WORKSPACE_MD),
                "inbox_md": str(INBOX_MD),
                "json": str(JSON_OUT),
                "csv": str(CSV_OUT),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


def main() -> None:
    records = load_raw_records()
    print(
        json.dumps(
            {
                "initial_filtered": len(records),
                "initial_one_week": sum(1 for r in records.values() if r["is_one_week"]),
                "one_week_cutoff": ONE_WEEK_CUTOFF.isoformat(),
                "two_week_cutoff": TWO_WEEK_CUTOFF.isoformat(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    failures = []
    if len(records) < TARGET:
        failures = collect_more(records)
    rows, window = select_rows(records)
    write_outputs(rows, window, failures, records)


if __name__ == "__main__":
    main()
