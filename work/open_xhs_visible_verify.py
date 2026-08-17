from __future__ import annotations

import time
from pathlib import Path
import sys


SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
sys.path.insert(0, str(SKILL_DIR))

from scripts.client import XiaohongshuClient


def main() -> None:
    url = "https://www.xiaohongshu.com/user/profile/6923c5b90000000032025bae"
    client = XiaohongshuClient(headless=False)
    client.start()
    try:
        page = client.page
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("visible_xhs_window_open", flush=True)
        print(url, flush=True)
        time.sleep(600)
    finally:
        client.close()


if __name__ == "__main__":
    main()
