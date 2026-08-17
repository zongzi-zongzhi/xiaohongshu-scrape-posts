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
PROFILE_DIR = Path.home() / ".xiaohongshu" / "browser-data"
PROXY = "http://127.0.0.1:18089"
QR_IMAGE = WORK_DIR / "xhs_crawler_profile_login_qr.png"
FULL_IMAGE = WORK_DIR / "xhs_crawler_profile_login_page.png"
STATE_JSON = WORK_DIR / "xhs_crawler_profile_login_qr_state.json"


def write_state(**kwargs) -> None:
    payload = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **kwargs}
    STATE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def login_state(context, page) -> dict:
    cookies = context.cookies("https://www.xiaohongshu.com")
    cookie_names = sorted({cookie.get("name", "") for cookie in cookies})
    text = page.evaluate("() => document.body.innerText.slice(0, 1600)")
    login_markers = ["登录后推荐更懂你的笔记", "手机号登录", "获取验证码", "扫码", "登录"]
    verify_markers = ["安全验证", "扫码验证身份", "拖动滑块", "保护账号安全"]
    return {
        "url": page.url,
        "cookie_names": cookie_names,
        "has_web_session_cookie": "web_session" in cookie_names,
        "has_a1_cookie": "a1" in cookie_names,
        "login_marker_present": any(marker in text for marker in login_markers),
        "verify_marker_present": any(marker in text for marker in verify_markers),
        "text_sample": text[:300],
    }


def save_qr_screenshot(page) -> str:
    page.screenshot(path=str(FULL_IMAGE), full_page=True)
    candidates = page.evaluate(
        """() => Array.from(document.querySelectorAll('canvas,img')).map((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                index,
                tag: el.tagName.toLowerCase(),
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                visible: rect.width > 80 && rect.height > 80 && style.visibility !== 'hidden' && style.display !== 'none',
                src: el.getAttribute('src') || '',
                alt: el.getAttribute('alt') || '',
            };
        }).filter(item => item.visible && Math.abs(item.width - item.height) < 40)
          .sort((a, b) => (b.width * b.height) - (a.width * a.height));"""
    )
    if candidates:
        box = candidates[0]
        try:
            page.screenshot(
                path=str(QR_IMAGE),
                clip={
                    "x": max(0, box["x"] - 12),
                    "y": max(0, box["y"] - 12),
                    "width": min(box["width"] + 24, 1440),
                    "height": min(box["height"] + 24, 1000),
                },
            )
            return "qr_crop"
        except Exception as exc:
            QR_IMAGE.write_bytes(FULL_IMAGE.read_bytes())
            write_state(status="qr_crop_failed_full_page_fallback", error=f"{type(exc).__name__}: {exc}", qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE))
            return "full_page_fallback"
    QR_IMAGE.write_bytes(FULL_IMAGE.read_bytes())
    return "full_page_fallback"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=900)
    args = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    write_state(status="starting", profile=str(PROFILE_DIR), qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE))

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
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
        image_mode = save_qr_screenshot(page)
        state = login_state(context, page)
        write_state(status="waiting_for_scan", image_mode=image_mode, qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE), **state)
        print(json.dumps({"status": "waiting_for_scan", "qr_image": str(QR_IMAGE), "full_image": str(FULL_IMAGE), **state}, ensure_ascii=False), flush=True)

        deadline = time.time() + args.seconds
        while time.time() < deadline:
            page.wait_for_timeout(5000)
            state = login_state(context, page)
            if state["has_web_session_cookie"] and not state["login_marker_present"] and not state["verify_marker_present"]:
                write_state(status="logged_in", qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE), **state)
                break
            write_state(status="waiting_for_scan", qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE), **state)
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
