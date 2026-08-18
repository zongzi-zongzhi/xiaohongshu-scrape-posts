from __future__ import annotations

import py_compile
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectHealthTest(unittest.TestCase):
    def test_required_project_files_exist(self) -> None:
        required = [
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            "SECURITY.md",
            "CONTRIBUTING.md",
            ".env.example",
            "pyproject.toml",
            "docs/PRD.md",
            "docs/TECH_ARCHITECTURE.md",
            "docs/PROJECT_STRUCTURE.md",
            "docs/DEV_LOG.md",
            "src/xiaohongshu_scrape_posts/rules.py",
            "src/xiaohongshu_scrape_posts/quality.py",
            "src/xiaohongshu_scrape_posts/feedback.py",
            "src/xiaohongshu_scrape_posts/integrations/lark.py",
            "scripts/xhs_cli.py",
            "examples/sample_rules.md",
            "examples/sample_rows.json",
        ]
        missing = [path for path in required if not (ROOT / path).exists()]
        self.assertEqual([], missing)

    def test_gitignore_covers_sensitive_runtime_paths(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in [
            ".env",
            "outputs/",
            "cookies.json",
            "storage_state.json",
            "browser-data*/",
            "work/*",
            "work/**/*.json",
            "work/**/*.log",
            "*.png",
        ]:
            self.assertIn(pattern, text)

    def test_key_scripts_compile(self) -> None:
        scripts = [
            "scripts/xhs_cli.py",
            "src/xiaohongshu_scrape_posts/cli.py",
            "src/xiaohongshu_scrape_posts/rules.py",
            "src/xiaohongshu_scrape_posts/quality.py",
            "src/xiaohongshu_scrape_posts/feedback.py",
            "src/xiaohongshu_scrape_posts/paths.py",
            "src/xiaohongshu_scrape_posts/crawler/legacy.py",
            "src/xiaohongshu_scrape_posts/integrations/lark.py",
            "work/append_xhs_rows_to_fixed_lark_master.py",
            "work/bound_connect_proxy.py",
            "work/check_xhs_crawler_profile_20260809.py",
            "work/crawl_xhs_incremental_20260727_20260728_merge_existing.py",
            "work/open_xhs_new_profile_login.py",
            "work/xhs_lead_quality.py",
            "work/xhs_no_reply_filter.py",
            "work/xhs_rules_doc.py",
        ]
        for script in scripts:
            with self.subTest(script=script):
                py_compile.compile(str(ROOT / script), doraise=True)

    def test_no_obvious_secret_literals_in_tracked_docs_or_source(self) -> None:
        patterns = [
            re.compile(r"https://[a-z0-9-]+\.feishu\.cn/base/[A-Za-z0-9]{20,}", re.I),
            re.compile(r"\b(?:app_secret|client_secret|password)\s*=\s*['\"][^'\"]+['\"]", re.I),
            re.compile(r"\bXHS_LARK_BASE_TOKEN\s*=\s*(?!your_)[A-Za-z0-9_-]{12,}", re.I),
            re.compile(r"AKIA[0-9A-Z]{16}"),
        ]
        checked_suffixes = {".md", ".py", ".yml", ".yaml", ".example", ".toml"}
        offenders: list[str] = []
        candidates = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        for relative in candidates:
            path = ROOT / relative
            if path.is_dir() or path.suffix not in checked_suffixes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                offenders.append(relative)
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
