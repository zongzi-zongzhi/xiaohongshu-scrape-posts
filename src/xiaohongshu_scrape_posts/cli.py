from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import rules
from .crawler import legacy
from .paths import PROJECT_ROOT


def run_module(module: str, args: list[str]) -> int:
    command = [sys.executable, "-m", module, *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=legacy.python_env(), check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xhs-leads",
        description="Xiaohongshu InsForge lead scraping automation CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("rules", help="Print normalized rule document metadata.")
    subparsers.add_parser("health", help="Run static project health checks.")
    subparsers.add_parser("check-login", help="Check Xiaohongshu crawler profile login state.")
    subparsers.add_parser("open-login", help="Open a visible Xiaohongshu login window.")

    crawl_parser = subparsers.add_parser("crawl", help="Run the incremental crawler through the compatibility entry.")
    crawl_parser.add_argument("--script", type=Path, help="Optional crawl script path. Defaults to the baseline incremental crawler.")

    subparsers.add_parser("append", help="Append local JSON rows to the fixed Feishu Base. Pass lark args after --.")
    subparsers.add_parser("feedback-profile", help="Refresh or inspect the no-reply feedback profile. Pass args after --.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    known, passthrough = parser.parse_known_args(argv)

    if known.command == "rules":
        print(json.dumps(rules.RULES.as_meta(), ensure_ascii=False, indent=2), flush=True)
        return 0
    if known.command == "health":
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=PROJECT_ROOT,
            check=False,
        ).returncode
    if known.command == "check-login":
        return legacy.check_login(passthrough)
    if known.command == "open-login":
        return legacy.open_login(passthrough)
    if known.command == "crawl":
        return legacy.crawl(passthrough, script=known.script)
    if known.command == "append":
        return run_module("xiaohongshu_scrape_posts.integrations.lark", passthrough)
    if known.command == "feedback-profile":
        return run_module("xiaohongshu_scrape_posts.feedback", passthrough)

    parser.error(f"Unknown command: {known.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
