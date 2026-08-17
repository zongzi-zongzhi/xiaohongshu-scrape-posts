from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


PROFILE_URL = "https://www.xiaohongshu.com/user/profile/67af195e000000000e01eced"
PROXY = "http://127.0.0.1:18089"


def main() -> None:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".xiaohongshu" / "browser-data"),
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
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
        print("visible_xhs_window_open", flush=True)
        print(page.url, flush=True)
        time.sleep(900)
        context.close()


if __name__ == "__main__":
    main()
