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
WORK = ROOT / "work"
PROFILE = Path.home() / ".xiaohongshu" / "browser-data-insforge-20260802"
PROXY = "http://127.0.0.1:18089"
VERIFY_STATE = WORK / "xhs_incremental_verify_required_state_20260809_20260810.json"
STATE_JSON = WORK / "xhs_verify_visible_state_20260810.json"
FULL_IMAGE = WORK / "xhs_verify_page_20260810_latest.png"
QR_IMAGE = WORK / "xhs_verify_qr_20260810_latest.png"
DEFAULT_URL = "https://www.xiaohongshu.com/explore"


LOGIN_MARKERS = ["登录后推荐更懂你的笔记", "手机号登录", "获取验证码", "扫码", "登录"]
VERIFY_MARKERS = ["安全验证", "扫码验证身份", "拖动滑块", "保护账号安全", "请勿频繁操作"]
EXPIRED_MARKERS = ["二维码已过期", "点击刷新", "已失效"]


def write_state(**kwargs) -> None:
    payload = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **kwargs}
    STATE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def target_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url
    if VERIFY_STATE.exists():
        try:
            data = json.loads(VERIFY_STATE.read_text(encoding="utf-8"))
            url = str(data.get("url") or "").strip()
            if url:
                return url
        except Exception:
            pass
    return DEFAULT_URL


def read_page_state(context, page) -> dict:
    cookies = context.cookies("https://www.xiaohongshu.com")
    cookie_names = sorted({str(cookie.get("name") or "") for cookie in cookies})
    try:
        text = page.evaluate("() => document.body ? document.body.innerText.slice(0, 2200) : ''")
    except Exception:
        text = ""
    return {
        "url": page.url,
        "profile": str(PROFILE),
        "full_image": str(FULL_IMAGE),
        "qr_image": str(QR_IMAGE) if QR_IMAGE.exists() else "",
        "cookie_names": cookie_names,
        "has_web_session_cookie": "web_session" in cookie_names,
        "has_a1_cookie": "a1" in cookie_names,
        "login_marker_present": any(marker in text for marker in LOGIN_MARKERS),
        "verify_marker_present": any(marker in text for marker in VERIFY_MARKERS),
        "frequent_operation_present": "请勿频繁操作" in text,
        "expired_marker_present": any(marker in text for marker in EXPIRED_MARKERS),
        "text_sample": text[:600],
    }


def candidate_boxes(page) -> list[dict]:
    script = """() => {
      const items = [];
      const elements = Array.from(document.querySelectorAll('canvas,img,svg'));
      for (const [index, el] of elements.entries()) {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const visible = rect.width > 70 && rect.height > 70 &&
          style.visibility !== 'hidden' && style.display !== 'none' &&
          Number(style.opacity || '1') > 0.2;
        if (!visible) continue;
        const squareish = Math.abs(rect.width - rect.height) <= Math.max(48, Math.min(rect.width, rect.height) * 0.35);
        const src = el.getAttribute('src') || '';
        const alt = el.getAttribute('alt') || '';
        const cls = el.getAttribute('class') || '';
        const label = `${src} ${alt} ${cls}`.toLowerCase();
        const qrish = label.includes('qr') || label.includes('code') || label.includes('captcha');
        if (squareish || qrish) {
          items.push({
            index,
            tag: el.tagName.toLowerCase(),
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            area: rect.width * rect.height,
            src: src.slice(0, 160),
            alt,
            className: cls,
            score: (qrish ? 1000000 : 0) + rect.width * rect.height
          });
        }
      }
      return items.sort((a, b) => b.score - a.score).slice(0, 8);
    }"""
    try:
        return page.evaluate(script) or []
    except Exception:
        return []


def save_images(page) -> dict:
    result = {"full_image": str(FULL_IMAGE), "qr_image": "", "qr_crop_mode": "none", "qr_candidates": []}
    try:
        page.screenshot(path=str(FULL_IMAGE), full_page=True)
    except Exception as exc:
        result["screenshot_error"] = f"{type(exc).__name__}: {exc}"
        return result

    boxes = candidate_boxes(page)
    result["qr_candidates"] = boxes
    if not boxes:
        return result

    box = boxes[0]
    clip = {
        "x": max(0, float(box["x"]) - 24),
        "y": max(0, float(box["y"]) - 24),
        "width": min(float(box["width"]) + 48, 1440),
        "height": min(float(box["height"]) + 48, 1000),
    }
    try:
        page.screenshot(path=str(QR_IMAGE), clip=clip)
        result["qr_image"] = str(QR_IMAGE)
        result["qr_crop_mode"] = "element_crop"
    except Exception as exc:
        result["qr_crop_error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--url", default="")
    args = parser.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    url = target_url(args.url.strip() or None)
    write_state(status="starting", url=url, profile=str(PROFILE), full_image=str(FULL_IMAGE), qr_image="")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
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
                "--start-maximized",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.bring_to_front()
        try:
            page.goto(url, wait_until="commit", timeout=15000)
        except Exception as exc:
            write_state(
                status="navigation_timeout",
                url=url,
                profile=str(PROFILE),
                full_image=str(FULL_IMAGE),
                qr_image=str(QR_IMAGE) if QR_IMAGE.exists() else "",
                navigation_error=f"{type(exc).__name__}: {exc}",
            )
        page.wait_for_timeout(6000)

        images = save_images(page)
        state = read_page_state(context, page)
        write_state(status="waiting_for_user", **images, **state)
        print(json.dumps({"status": "waiting_for_user", **images, **state}, ensure_ascii=False), flush=True)

        deadline = time.time() + args.seconds
        while time.time() < deadline:
            page.wait_for_timeout(5000)
            images = save_images(page)
            state = read_page_state(context, page)
            if state["has_web_session_cookie"] and not state["login_marker_present"] and not state["verify_marker_present"]:
                write_state(status="passed", **images, **state)
                print(json.dumps({"status": "passed", **images, **state}, ensure_ascii=False), flush=True)
                break
            write_state(status="waiting_for_user", **images, **state)

        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
