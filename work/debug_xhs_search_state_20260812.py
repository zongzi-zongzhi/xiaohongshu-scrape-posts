from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

import collect_xhs_expanded_leads_with_comments as expanded
import collect_xhs_since_last_crawl as base


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"


def main() -> int:
    keyword = os.environ.get("XHS_DEBUG_KEYWORD", "Supabase 新手")
    out = WORK / "xhs_debug_search_state_20260812.json"
    shot = WORK / "xhs_debug_search_state_20260812.png"
    url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_explore_feed"
    with sync_playwright() as p:
        context = expanded.browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        result: dict[str, object] = {"keyword": keyword, "url": url}
        try:
            page.goto(url, wait_until="commit", timeout=45000)
            page.wait_for_timeout(10000)
            base.dismiss_login_popup(page)
            page.wait_for_timeout(2000)
            text = page.evaluate("() => document.body.innerText.slice(0, 3000)")
            state = page.evaluate(
                """() => {
                  const feeds = window.__INITIAL_STATE__?.search?.feeds;
                  const arr = feeds?.value || feeds?._value || [];
                  return {
                    href: location.href,
                    title: document.title,
                    text: document.body.innerText.slice(0, 3000),
                    hasInitialState: !!window.__INITIAL_STATE__,
                    searchKeys: Object.keys(window.__INITIAL_STATE__?.search || {}),
                    feedCount: Array.isArray(arr) ? arr.length : -1,
                    firstFeed: Array.isArray(arr) && arr.length ? arr[0] : null,
                    htmlSample: document.documentElement.outerHTML.slice(0, 2000)
                  };
                }"""
            )
            result.update({"status": "ok", "visible_text": text, "state": state})
            try:
                page.screenshot(path=str(shot), full_page=True)
                result["screenshot"] = str(shot)
            except Exception as exc:
                result["screenshot_error"] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            result.update({"status": "error", "error": f"{type(exc).__name__}: {exc}", "current_url": page.url})
            try:
                page.screenshot(path=str(shot), full_page=True)
                result["screenshot"] = str(shot)
            except Exception as shot_exc:
                result["screenshot_error"] = f"{type(shot_exc).__name__}: {shot_exc}"
        finally:
            context.close()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
