from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "work"
DEFAULT_PROFILE_DIR = Path.home() / ".xiaohongshu" / "browser-data-insforge-20260802"
PROXY = "http://127.0.0.1:18089"
STATE_JSON = WORK_DIR / "xhs_new_profile_login_state_20260802.json"
FULL_IMAGE = WORK_DIR / "xhs_new_profile_login_page_20260802.png"


def write_state(**kwargs) -> None:
    payload = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **kwargs}
    STATE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def login_state(context, page) -> dict:
    cookies = context.cookies("https://www.xiaohongshu.com")
    cookie_names = sorted({cookie.get("name", "") for cookie in cookies})
    text = page.evaluate("() => document.body.innerText.slice(0, 1800)")
    login_markers = ["登录后推荐更懂你的笔记", "手机号登录", "获取验证码", "扫码", "登录"]
    verify_markers = ["安全验证", "扫码验证身份", "拖动滑块", "保护账号安全", "请勿频繁操作"]
    return {
        "url": page.url,
        "cookie_names": cookie_names,
        "has_web_session_cookie": "web_session" in cookie_names,
        "has_a1_cookie": "a1" in cookie_names,
        "login_marker_present": any(marker in text for marker in login_markers),
        "verify_marker_present": any(marker in text for marker in verify_markers),
        "text_sample": text[:400],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR))
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--url", default="https://www.xiaohongshu.com/explore")
    parser.add_argument("--keep-open", action="store_true", help="Keep the visible browser open even after login/verification passes.")
    args = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(args.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    write_state(status="starting", profile=str(profile_dir), full_image=str(FULL_IMAGE))

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
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
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        try:
            page.screenshot(path=str(FULL_IMAGE), full_page=True)
        except Exception:
            pass
        state = login_state(context, page)
        write_state(status="waiting_for_login", profile=str(profile_dir), full_image=str(FULL_IMAGE), **state)
        print(
            json.dumps(
                {"status": "waiting_for_login", "profile": str(profile_dir), "full_image": str(FULL_IMAGE), **state},
                ensure_ascii=False,
            ),
            flush=True,
        )

        deadline = time.time() + args.seconds
        reported_logged_in = False
        while time.time() < deadline:
            page.wait_for_timeout(5000)
            state = login_state(context, page)
            if state["has_web_session_cookie"] and not state["login_marker_present"] and not state["verify_marker_present"]:
                write_state(status="logged_in", profile=str(profile_dir), full_image=str(FULL_IMAGE), **state)
                if not reported_logged_in:
                    print(json.dumps({"status": "logged_in", "profile": str(profile_dir), **state}, ensure_ascii=False), flush=True)
                    reported_logged_in = True
                if not args.keep_open:
                    break
                continue
            write_state(status="waiting_for_login", profile=str(profile_dir), full_image=str(FULL_IMAGE), **state)
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
