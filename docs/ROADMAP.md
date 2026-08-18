# Roadmap

## Near Term

- Keep the unified CLI as the only documented entrypoint.
- Continue moving stable crawler logic from `work/` into `src/xiaohongshu_scrape_posts/`.
- Keep the rule document parser tolerant of human-edited Markdown.
- Improve quality scoring with more Feishu feedback signals.

## Later

- Add a clean source adapter boundary so Xiaohongshu can be replaced or complemented by other platforms.
- Add dry-run reports that explain why each candidate was accepted or rejected.
- Add fixture-based tests for rule parsing, feedback learning, and Feishu row normalization.
