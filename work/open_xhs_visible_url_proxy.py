from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
VERIFY_STATE_JSON = ROOT / "work" / "xhs_verify_required_state.json"
PROXY = "http://127.0.0.1:18089"
DEFAULT_PROFILE_DIR = Path(r"C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="")
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--profile-dir", default="")
    args = parser.parse_args()

    url = args.url
    if not url and VERIFY_STATE_JSON.exists():
        data = json.loads(VERIFY_STATE_JSON.read_text(encoding="utf-8"))
        url = data.get("url", "")
    if not url:
        url = "https://www.xiaohongshu.com/explore"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.profile_dir
            or os.environ.get("XHS_BROWSER_PROFILE_DIR")
            or str(DEFAULT_PROFILE_DIR),
            headless=False,
            proxy={"server": PROXY},
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=AutomationControlled",
                "--disable-infobars",
                "--disable-session-crashed-bubble",
                "--hide-crash-restore-bubble",
                "--no-first-run",
                "--restore-last-session=false",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("visible_xhs_window_open", flush=True)
        print(page.url, flush=True)
        time.sleep(args.seconds)
        context.close()


if __name__ == "__main__":
    main()
