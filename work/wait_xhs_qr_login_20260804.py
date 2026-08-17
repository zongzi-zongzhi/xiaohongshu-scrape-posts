from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
PROFILE = Path.home() / ".xiaohongshu" / "browser-data-insforge-20260802"
PROXY = "http://127.0.0.1:18089"
FULL_IMAGE = WORK / "xhs_login_page_20260804_live.png"
QR_IMAGE = WORK / "xhs_login_qr_20260804_live.png"
STATE_JSON = WORK / "xhs_login_qr_20260804_live_state.json"


def write_state(**payload) -> None:
    STATE_JSON.write_text(
        json.dumps({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def page_text(page) -> str:
    return page.evaluate("() => document.body.innerText.slice(0, 2500)")


def login_state(context, page, status: str) -> dict:
    text = page_text(page)
    cookies = context.cookies("https://www.xiaohongshu.com")
    cookie_names = sorted({cookie.get("name", "") for cookie in cookies})
    return {
        "status": status,
        "profile": str(PROFILE),
        "url": page.url,
        "qr_image": str(QR_IMAGE),
        "full_image": str(FULL_IMAGE),
        "has_web_session_cookie": "web_session" in cookie_names,
        "has_a1_cookie": "a1" in cookie_names,
        "login_marker_present": any(
            marker in text for marker in ["登录后推荐更懂你的笔记", "手机号登录", "获取验证码", "扫码", "登录"]
        ),
        "verify_marker_present": any(
            marker in text for marker in ["安全验证", "扫码验证身份", "拖动滑块", "保护账号安全", "请勿频繁操作"]
        ),
        "text_sample": text[:600],
    }


def crop_qr(page) -> str:
    page.screenshot(path=str(FULL_IMAGE), full_page=True)
    candidates = page.evaluate(
        """() => Array.from(document.querySelectorAll('canvas,img')).map((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const area = rect.width * rect.height;
            return {
                index,
                tag: el.tagName.toLowerCase(),
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                area,
                visible: rect.width > 80 && rect.height > 80 && style.visibility !== 'hidden' && style.display !== 'none',
            };
        }).filter(item => item.visible && Math.abs(item.width - item.height) < 80)
          .sort((a, b) => b.area - a.area);"""
    )
    if candidates:
        box = candidates[0]
        page.screenshot(
            path=str(QR_IMAGE),
            clip={
                "x": max(0, box["x"] - 18),
                "y": max(0, box["y"] - 18),
                "width": min(box["width"] + 36, 1440),
                "height": min(box["height"] + 36, 1000),
            },
        )
        return "auto_crop"

    # Fallback for the current login modal layout.
    img = Image.open(FULL_IMAGE)
    crop = img.crop((430, 415, 598, 583))
    crop = crop.resize((420, 420), Image.Resampling.NEAREST)
    crop.save(QR_IMAGE)
    return "layout_fallback"


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    write_state(status="starting", profile=str(PROFILE), qr_image=str(QR_IMAGE), full_image=str(FULL_IMAGE))

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
        page.set_default_timeout(25000)
        page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        text = page_text(page)
        if "手机号登录" not in text and "扫码" not in text:
            try:
                page.get_by_text("登录").first.click(timeout=5000)
                page.wait_for_timeout(3000)
            except Exception:
                pass
        text = page_text(page)
        if "二维码已过期" in text or "点击刷新" in text:
            try:
                page.get_by_text("点击刷新").click(timeout=5000)
                page.wait_for_timeout(4000)
            except Exception:
                pass
        crop_mode = crop_qr(page)
        state = login_state(context, page, "waiting_for_scan")
        state["crop_mode"] = crop_mode
        write_state(**state)
        print(json.dumps(state, ensure_ascii=False), flush=True)

        deadline = time.time() + 900
        while time.time() < deadline:
            page.wait_for_timeout(5000)
            state = login_state(context, page, "waiting_for_scan")
            state["crop_mode"] = crop_mode
            if state["has_web_session_cookie"] and not state["login_marker_present"] and not state["verify_marker_present"]:
                state["status"] = "logged_in"
                write_state(**state)
                print(json.dumps(state, ensure_ascii=False), flush=True)
                break
            write_state(**state)
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
