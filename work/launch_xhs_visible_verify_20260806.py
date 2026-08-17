from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
PROFILE = Path(r"C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802")
URL = "https://www.xiaohongshu.com/search_result/?keyword=Supabase%20RLS%20%E6%9D%83%E9%99%90"


def main() -> int:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout_path = WORK / f"xhs_visible_verify_20260806_newui_{ts}_stdout.log"
    stderr_path = WORK / f"xhs_visible_verify_20260806_newui_{ts}_stderr.log"
    stdout = stdout_path.open("w", encoding="utf-8")
    stderr = stderr_path.open("w", encoding="utf-8")
    cmd = [
        sys.executable,
        str(WORK / "open_xhs_new_profile_login.py"),
        "--profile-dir",
        str(PROFILE),
        "--url",
        URL,
        "--seconds",
        "900",
    ]
    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
        close_fds=True,
    )
    print(
        json.dumps(
            {
                "pid": proc.pid,
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "profile": str(PROFILE),
                "url": URL,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
