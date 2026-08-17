from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

import collect_xhs_expanded_leads_with_comments as expanded


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = expanded.ROOT
LIVE_CACHE_JSON = expanded.OUT_DIR / f"xhs_expanded_live_candidates_cache_{expanded.START_LABEL}_{expanded.END_LABEL}.json"
VERIFY_STATE_JSON = ROOT / "work" / "xhs_verify_required_state.json"
VERIFY_SCREENSHOT = ROOT / "work" / "xhs_verify_required.png"


def load_cache() -> tuple[dict[str, dict], set[int], list[dict[str, str]]]:
    if not LIVE_CACHE_JSON.exists():
        return expanded.load_seed_candidates(), set(), []
    data = json.loads(LIVE_CACHE_JSON.read_text(encoding="utf-8"))
    candidates: dict[str, dict] = {}
    for row in data.get("candidates", []):
        if row.get("note_id"):
            candidates[row["note_id"]] = row
    completed = {int(item) for item in data.get("completed_keyword_indexes", [])}
    failures = [item for item in data.get("failures", []) if isinstance(item, dict)]
    if not candidates:
        candidates = expanded.load_seed_candidates()
    return candidates, completed, failures


def save_cache(candidates: dict[str, dict], completed: set[int], failures: list[dict[str, str]], *, current_index: int | None = None, current_keyword: str = "") -> None:
    keepable = expanded.classify_and_select(list(candidates.values()), expanded.TARGET, fetch_ready=False)
    payload = {
        "meta": {
            "updated_at": datetime.now(expanded.TZ).isoformat(),
            "window_start": expanded.SEVEN_DAY_START.isoformat(),
            "window_end": expanded.NOW.isoformat(),
            "keywords_count": len(expanded.KEYWORDS),
            "completed_count": len(completed),
            "current_index": current_index,
            "current_keyword": current_keyword,
            "candidate_count": len(candidates),
            "keepable_count": len(keepable),
            "level_counts": level_counts(keepable),
        },
        "completed_keyword_indexes": sorted(completed),
        "failures": failures,
        "candidates": list(candidates.values()),
    }
    LIVE_CACHE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def level_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        level = row.get("线索等级", "")
        counts[level] = counts.get(level, 0) + 1
    return counts


def is_verify_text(text: str) -> bool:
    return any(marker in text for marker in ["扫码验证身份", "保护账号安全", "安全验证", "拖动滑块", "请完成验证"])


def capture_verify(page, *, keyword: str, index: int) -> None:
    try:
        page.screenshot(path=str(VERIFY_SCREENSHOT), full_page=True)
    except Exception:
        pass
    VERIFY_STATE_JSON.write_text(
        json.dumps(
            {
                "detected_at": datetime.now(expanded.TZ).isoformat(),
                "keyword": keyword,
                "keyword_index": index,
                "url": page.url,
                "screenshot": str(VERIFY_SCREENSHOT),
                "message": "小红书触发安全验证。请扫码或在打开的浏览器窗口中完成验证后继续运行。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def search_keyword(page, candidates: dict[str, dict], keyword: str, index: int, scroll_rounds: int) -> str:
    url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_explore_feed"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(random.randint(4200, 6400))
    expanded.base.dismiss_login_popup(page)
    visible = page.evaluate("() => document.body.innerText.slice(0, 1600)")
    if is_verify_text(visible):
        capture_verify(page, keyword=keyword, index=index)
        return "verify_required"

    stable_rounds = 0
    last_total = len(candidates)
    for _ in range(scroll_rounds):
        items = expanded.extract_items_from_search(page, keyword)
        for item in items:
            note_id = str(item.get("id") or "").strip()
            published_at = expanded.parse_dt(None, note_id)
            if not published_at or published_at < expanded.SEVEN_DAY_START or published_at > expanded.NOW:
                continue
            row = expanded.normalize_candidate(
                {
                    "note_id": note_id,
                    "xsec_token": item.get("xsec_token"),
                    "title": item.get("title"),
                    "desc": item.get("desc"),
                    "liked_count": item.get("liked_count"),
                    "comment_count": item.get("comment_count"),
                    "collected_count": item.get("collected_count"),
                    "author": item.get("author"),
                    "author_id": item.get("author_id"),
                    "author_xsec_token": item.get("author_xsec_token"),
                    "keyword": keyword,
                    "published_at": published_at.isoformat(),
                },
                "live_search_resume",
            )
            expanded.add_candidate(candidates, row)
        if len(candidates) == last_total:
            stable_rounds += 1
        else:
            stable_rounds = 0
        last_total = len(candidates)
        if stable_rounds >= 2:
            break
        page.mouse.wheel(0, random.randint(1600, 2600))
        page.wait_for_timeout(random.randint(900, 1500))
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-index", type=int, default=53, help="1-based keyword index to start from when no cache exists")
    parser.add_argument("--scroll-rounds", type=int, default=7)
    args = parser.parse_args()

    candidates, completed, failures = load_cache()
    if not completed and args.start_index > 1:
        completed.update(range(1, args.start_index))
    print(f"cache candidates={len(candidates)} completed={len(completed)}/{len(expanded.KEYWORDS)}", flush=True)
    save_cache(candidates, completed, failures)

    with sync_playwright() as p:
        context = expanded.browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        try:
            for index, keyword in enumerate(expanded.KEYWORDS, start=1):
                if index in completed:
                    continue
                print(f"search [{index}/{len(expanded.KEYWORDS)}] {keyword}", flush=True)
                try:
                    status = search_keyword(page, candidates, keyword, index, args.scroll_rounds)
                    if status == "verify_required":
                        failures.append({"keyword": keyword, "index": str(index), "error": "verify_required"})
                        save_cache(candidates, completed, failures, current_index=index, current_keyword=keyword)
                        print(json.dumps({"status": "verify_required", "keyword": keyword, "index": index, "screenshot": str(VERIFY_SCREENSHOT)}, ensure_ascii=False), flush=True)
                        return 20
                    completed.add(index)
                    save_cache(candidates, completed, failures, current_index=index, current_keyword=keyword)
                    keepable = expanded.classify_and_select(list(candidates.values()), expanded.TARGET, fetch_ready=False)
                    print(f"checkpoint candidates={len(candidates)} keepable={len(keepable)} levels={level_counts(keepable)}", flush=True)
                except Exception as exc:
                    failures.append({"keyword": keyword, "index": str(index), "error": f"{type(exc).__name__}: {exc}"})
                    save_cache(candidates, completed, failures, current_index=index, current_keyword=keyword)
                    print(f"search error {index} {keyword}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                time.sleep(random.uniform(0.9, 1.8))
        finally:
            context.close()

    save_cache(candidates, completed, failures)
    print(json.dumps({"status": "complete", "cache": str(LIVE_CACHE_JSON), "candidates": len(candidates), "completed": len(completed)}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
