# Project Structure

## Public Source

```text
scripts/xhs_cli.py
src/xiaohongshu_scrape_posts/
  __init__.py
  cli.py
  feedback.py
  paths.py
  quality.py
  rules.py
  crawler/
    __init__.py
    legacy.py
  integrations/
    __init__.py
    lark.py
```

## Compatibility Scripts

`work/` is ignored by default. Only these maintained Xiaohongshu compatibility files are public:

- `work/append_xhs_rows_to_fixed_lark_master.py`
- `work/bound_connect_proxy.py`
- `work/check_xhs_crawler_profile_20260809.py`
- `work/crawl_xhs_incremental_20260727_20260728_merge_existing.py`
- `work/open_xhs_new_profile_login.py`
- `work/xhs_lead_quality.py`
- `work/xhs_no_reply_filter.py`
- `work/xhs_rules_doc.py`

Everything else under `work/` is treated as runtime scratch, history, or local-only experiment.

## Ignored Runtime Data

- `outputs/`
- `logs/`
- browser profiles
- cookies and storage state
- Feishu payload JSON
- screenshots
- raw scrape caches
- `.env` and other local secrets

## Docs And Examples

- `README.md`: quick start and operating contract.
- `docs/PRD.md`: product goal and scope.
- `docs/TECH_ARCHITECTURE.md`: runtime flow.
- `docs/PROJECT_STRUCTURE.md`: public repository boundary.
- `docs/ROADMAP.md`: future cleanup plan.
- `examples/sample_rules.md`: rule document example.
- `examples/sample_rows.json`: output row example.
- `examples/sample_output.md`: Markdown output example.

## Tests

- `tests/test_static_project_health.py`: public file boundary, compile check, and secret scan.
