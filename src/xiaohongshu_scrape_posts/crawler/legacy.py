from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..paths import PROJECT_ROOT


DEFAULT_CRAWL_SCRIPT = PROJECT_ROOT / "work" / "crawl_xhs_incremental_20260727_20260728_merge_existing.py"
DEFAULT_CHECK_LOGIN_SCRIPT = PROJECT_ROOT / "work" / "check_xhs_crawler_profile_20260809.py"
DEFAULT_OPEN_LOGIN_SCRIPT = PROJECT_ROOT / "work" / "open_xhs_new_profile_login.py"


def python_env() -> dict[str, str]:
    env = os.environ.copy()
    additions = [str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "work")]
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(additions + ([current] if current else []))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_script(script: Path, args: list[str] | None = None) -> int:
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")
    command = [sys.executable, str(script), *(args or [])]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=python_env(), check=False).returncode


def check_login(args: list[str] | None = None) -> int:
    return run_script(DEFAULT_CHECK_LOGIN_SCRIPT, args)


def open_login(args: list[str] | None = None) -> int:
    return run_script(DEFAULT_OPEN_LOGIN_SCRIPT, args)


def crawl(args: list[str] | None = None, script: Path | None = None) -> int:
    return run_script(script or DEFAULT_CRAWL_SCRIPT, args)
