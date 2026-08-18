from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


PROFILE = Path(os.environ.get("XHS_BROWSER_PROFILE_DIR") or Path.home() / ".xiaohongshu" / "browser-data-insforge-20260802")
PROXY = "http://127.0.0.1:18089"


def main() -> int:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=True,
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
        page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        text = page.evaluate("() => document.body.innerText.slice(0, 1800)")
        cookies = context.cookies("https://www.xiaohongshu.com")
        cookie_names = sorted({cookie.get("name", "") for cookie in cookies})
        login_markers = ["登录后推荐更懂你的笔记", "手机号登录", "获取验证码", "扫码", "登录"]
        verify_markers = ["安全验证", "扫码验证身份", "拖动滑块", "保护账号安全", "请勿频繁操作"]
        result = {
            "profile": str(PROFILE),
            "url": page.url,
            "has_web_session_cookie": "web_session" in cookie_names,
            "has_a1_cookie": "a1" in cookie_names,
            "login_marker_present": any(marker in text for marker in login_markers),
            "verify_marker_present": any(marker in text for marker in verify_markers),
            "cookie_names": cookie_names,
            "text_sample": text[:400],
        }
        context.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
