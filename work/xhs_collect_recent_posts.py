import csv
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
OUTPUT_DIR = ROOT / "outputs"
RAW_DIR = ROOT / "work" / "xhs_recent_raw"
INBOX_MD = Path(r"D:\czj note\00_Inbox\xhs_insforge_pain_posts_100_table.md")

sys.path.insert(0, str(SKILL_DIR))
from scripts import search as search_mod  # noqa: E402
from scripts.client import XiaohongshuClient  # noqa: E402
from scripts.search import SearchAction  # noqa: E402


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


def patch_filter_clicks() -> None:
    def patched(
        self,
        sort_by=None,
        note_type=None,
        publish_time=None,
        search_scope=None,
        location=None,
    ):
        page = self.client.page
        if not any([sort_by, note_type, publish_time, search_scope, location]):
            return

        try:
            page.locator("div.filter").hover()
            time.sleep(0.5)
            page.wait_for_selector("div.filter-panel", timeout=5000)
        except Exception as exc:
            print(f"filter-panel failed: {exc}", file=sys.stderr, flush=True)
            return

        filter_texts = []
        for group, value in [
            (1, sort_by),
            (2, note_type),
            (3, publish_time),
            (4, search_scope),
            (5, location),
        ]:
            if value:
                text = self._find_filter_text(group, value)
                if text:
                    filter_texts.append(text)

        panel = page.locator("div.filter-panel")
        for text in filter_texts:
            try:
                panel.get_by_text(text, exact=True).first.click()
                time.sleep(0.8)
            except Exception as exc:
                print(f"filter-click failed: {text} {exc}", file=sys.stderr, flush=True)
        time.sleep(2.5)

    SearchAction._apply_filters = patched


def patch_fast_navigation() -> None:
    def patched(self, url: str, wait_until: str = "domcontentloaded"):
        if not self.page:
            raise RuntimeError("Browser is not started")

        self._throttle()
        self._last_navigate_time = time.time()
        self._navigate_count += 1

        try:
            self.page.goto(url, wait_until="commit", timeout=30000)
        except Exception as exc:
            print(f"goto-commit failed, continuing: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

        time.sleep(3)
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=12000)
        except Exception:
            pass
        try:
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        if self._check_captcha():
            self._handle_captcha()

    XiaohongshuClient.navigate = patched


def patch_short_state_wait() -> None:
    def patched(self, timeout: int = 30000, retries: int = 2):
        if not self.page:
            raise RuntimeError("Browser is not started")
        if self._check_captcha():
            self._handle_captcha()
        try:
            self.page.wait_for_function(
                "() => window.__INITIAL_STATE__ !== undefined",
                timeout=8000,
            )
        except Exception:
            print("initial-state short wait timed out; continuing", file=sys.stderr, flush=True)

    XiaohongshuClient.wait_for_initial_state = patched


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
    mult = 1
    if text.endswith(("w", "万")):
        mult = 10000
        text = text[:-1]
    try:
        return int(float(text) * mult)
    except ValueError:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else 0


def repair_text(value: Any) -> str:
    text = "" if value is None else str(value)
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        return text
    if cjk_count(repaired) > cjk_count(text):
        return repaired
    return text


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def esc_md(value: Any) -> str:
    return repair_text(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def score_record(record: dict[str, Any]) -> int:
    haystack = f"{record.get('title', '')} {record.get('matched_keywords', '')}".lower()
    score = 0
    for term in PAIN_TERMS:
        if term.lower() in haystack:
            score += 3
    for term in TOPIC_TERMS:
        if term.lower() in haystack:
            score += 2
    return score


def search_once(keyword: str, variant: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    results = search_mod.search(
        keyword=keyword,
        sort_by=variant.get("sort_by"),
        publish_time=variant.get("publish_time"),
        limit=limit,
        headless=True,
    )
    return results or []


def collect_window(
    cutoff: datetime,
    variants: list[dict[str, Any]],
    target: int,
    existing: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    records = dict(existing or {})
    failures = []

    for variant_index, variant in enumerate(variants, start=1):
        before_variant = len(records)
        print(
            f"variant {variant_index}/{len(variants)} cutoff={cutoff.isoformat()} "
            f"sort={variant.get('sort_by')} time={variant.get('publish_time')}",
            flush=True,
        )

        for index, keyword in enumerate(KEYWORDS, start=1):
            print(f"[{index}/{len(KEYWORDS)}] {keyword}", flush=True)
            try:
                items = search_once(keyword, variant, limit=50)
            except Exception as exc:
                failures.append(
                    {
                        "keyword": keyword,
                        "variant": variant,
                        "error": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                time.sleep(8)
                continue

            raw_name = f"v{variant_index}_{safe_name(keyword)}.json"
            (RAW_DIR / raw_name).write_text(
                json.dumps({"variant": variant, "keyword": keyword, "results": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            for item in items:
                note_id = str(item.get("id") or "").strip()
                published_at = note_time(note_id)
                if not published_at or published_at < cutoff:
                    continue

                title = repair_text(item.get("title", "")).strip()
                author = repair_text(item.get("user", "")).strip()
                token = str(item.get("xsec_token") or "").strip()
                if not note_id or not title or not author or not token:
                    continue

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
                        "source_variant": [variant],
                    }
                else:
                    records[note_id]["matched_keywords"].append(keyword)
                    records[note_id]["source_variant"].append(variant)

            print(f"recent_count={len(records)}", flush=True)
            if len(records) >= target:
                break
            time.sleep(4 if index % 4 else 12)

        print(f"variant_added={len(records) - before_variant}", flush=True)
        if len(records) >= target:
            break
        time.sleep(15)

    return records, failures


def safe_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value).strip("_")


def make_url(note_id: str, token: str) -> str:
    return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search"


def select_top(records: dict[str, dict[str, Any]], target: int) -> list[dict[str, Any]]:
    rows = []
    for record in records.values():
        record = dict(record)
        record["matched_keywords"] = "、".join(dict.fromkeys(record.get("matched_keywords", [])))
        record["pain_score"] = score_record(record)
        record["engagement_score"] = (
            record["liked_count"]
            + record["collected_count"]
            + record["comment_count"] * 2
            + record["shared_count"] * 2
        )
        rows.append(record)
    rows.sort(
        key=lambda r: (
            r["pain_score"],
            r["comment_count"],
            r["engagement_score"],
            r["published_at"],
        ),
        reverse=True,
    )
    return rows[:target]


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

    headers = ["帖子标题", "帖子链接", "点赞", "评论", "收藏"]
    lines = ["| " + " | ".join(headers) + " |", "|---|---|---:|---:|---:|"]
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
                "json": str(json_path),
                "csv": str(csv_path),
                "workspace_md": str(md_path),
                "inbox_md": str(INBOX_MD),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
TARGET = 100


def main() -> None:
    patch_fast_navigation()
    patch_short_state_wait()
    patch_filter_clicks()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    one_week_cutoff = NOW - timedelta(days=7)
    two_week_cutoff = NOW - timedelta(days=14)

    one_week_variants = [
        {"sort_by": "最新", "publish_time": "一周内"},
        {"sort_by": None, "publish_time": "一周内"},
        {"sort_by": "最多评论", "publish_time": "一周内"},
        {"sort_by": "最多收藏", "publish_time": "一周内"},
    ]
    two_week_variants = [
        {"sort_by": "最新", "publish_time": "半年内"},
        {"sort_by": None, "publish_time": "半年内"},
        {"sort_by": "最多评论", "publish_time": "半年内"},
        {"sort_by": "最多收藏", "publish_time": "半年内"},
        {"sort_by": "最多点赞", "publish_time": "半年内"},
        {"sort_by": None, "publish_time": None},
    ]

    print(f"now={NOW.isoformat()}", flush=True)
    print(f"one_week_cutoff={one_week_cutoff.isoformat()}", flush=True)
    print(f"two_week_cutoff={two_week_cutoff.isoformat()}", flush=True)

    one_week_records, one_week_failures = collect_window(one_week_cutoff, one_week_variants, TARGET)
    used_window = "7_days"
    all_failures = list(one_week_failures)
    final_records = one_week_records

    if len(one_week_records) < TARGET:
        print(f"one_week_not_enough={len(one_week_records)}; expanding_to_14_days", flush=True)
        two_week_records, two_week_failures = collect_window(
            two_week_cutoff,
            two_week_variants,
            TARGET,
            existing=one_week_records,
        )
        final_records = two_week_records
        all_failures.extend(two_week_failures)
        used_window = "14_days" if len(two_week_records) >= TARGET else "14_days_partial"
    else:
        print(f"one_week_enough={len(one_week_records)}", flush=True)

    rows = select_top(final_records, TARGET)
    meta = {
        "generated_at": datetime.now(TZ).isoformat(),
        "now": NOW.isoformat(),
        "selection_window": used_window,
        "one_week_cutoff": one_week_cutoff.isoformat(),
        "two_week_cutoff": two_week_cutoff.isoformat(),
        "one_week_candidate_count": len(one_week_records),
        "final_candidate_count": len(final_records),
        "selected_count": len(rows),
        "keywords": KEYWORDS,
        "failures": all_failures,
        "note": "Only public search/detail data was read. No like/comment/favorite/message/publish actions were performed.",
    }
    write_outputs(rows, meta)


if __name__ == "__main__":
    main()
