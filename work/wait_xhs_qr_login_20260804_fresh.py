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
FULL_IMAGE = WORK / "xhs_login_page_20260804_fresh.png"
QR_IMAGE = WORK / "xhs_login_qr_20260804_fresh.png"
STATE_JSON = WORK / "xhs_login_qr_20260804_fresh_state.json"


LOGIN_LABELS = [
    "\u767b\u5f55\u540e\u63a8\u8350\u66f4\u61c2\u4f60\u7684\u7b14\u8bb0",
    "\u624b\u673a\u53f7\u767b\u5f55",
    "\u83b7\u53d6\u9a8c\u8bc1\u7801",
    "\u626b\u7801",
    "\u767b\u5f55",
]
VERIFY_LABELS = [
    "\u5b89\u5168\u9a8c\u8bc1",
    "\u626b\u7801\u9a8c\u8bc1\u8eab\u4efd",
    "\u62d6\u52a8\u6ed1\u5757",
    "\u4fdd\u62a4\u8d26\u53f7\u5b89\u5168",
    "\u8bf7\u52ff\u9891\u7e41\u64cd\u4f5c",
]
EXPIRED_LABELS = ["\u4e8c\u7ef4\u7801\u5df2\u8fc7\u671f", "\u70b9\u51fb\u5237\u65b0"]


def write_state(**payload) -> None:
    STATE_JSON.write_text(
        json.dumps({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def page_flags(page) -> dict:
    return page.evaluate(
        """(labels) => {
            const text = document.body ? (document.body.innerText || '') : '';
            return {
                login_marker_present: labels.login.some((label) => text.includes(label)),
                verify_marker_present: labels.verify.some((label) => text.includes(label)),
                expired_marker_present: labels.expired.some((label) => text.includes(label)),
                text_sample: text.slice(0, 600),
            };
        }""",
        {"login": LOGIN_LABELS, "verify": VERIFY_LABELS, "expired": EXPIRED_LABELS},
    )


def click_first_text(page, labels: list[str]) -> bool:
    return bool(
        page.evaluate(
            """(labels) => {
                const nodes = Array.from(document.querySelectorAll('button, div, span, a'));
                const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                };
                const target = nodes.find((el) => visible(el) && labels.some((label) => (el.innerText || '').includes(label)));
                if (!target) return false;
                target.click();
                return true;
            }""",
            labels,
        )
    )


def login_state(context, page, status: str) -> dict:
    cookies = context.cookies("https://www.xiaohongshu.com")
    cookie_names = sorted({cookie.get("name", "") for cookie in cookies})
    flags = page_flags(page)
    return {
        "status": status,
        "profile": str(PROFILE),
        "url": page.url,
        "qr_image": str(QR_IMAGE),
        "full_image": str(FULL_IMAGE),
        "has_web_session_cookie": "web_session" in cookie_names,
        "has_a1_cookie": "a1" in cookie_names,
        **flags,
    }


def crop_qr(page) -> str:
    page.screenshot(path=str(FULL_IMAGE), full_page=True)
    image = Image.open(FULL_IMAGE)
    # Current XHS login modal in a 1440x1000 viewport. Includes a quiet white border for scanning.
    crop = image.crop((418, 403, 610, 595))
    crop = crop.resize((480, 480), Image.Resampling.NEAREST)
    crop.save(QR_IMAGE)
    return "login_modal_fixed_crop"


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

        flags = page_flags(page)
        if not flags["login_marker_present"]:
            click_first_text(page, ["\u767b\u5f55"])
            page.wait_for_timeout(3000)

        flags = page_flags(page)
        if flags["expired_marker_present"]:
            if click_first_text(page, ["\u70b9\u51fb\u5237\u65b0"]):
                page.wait_for_timeout(5000)

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
