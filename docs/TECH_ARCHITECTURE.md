# Technical Architecture

## Flow

```text
Rule document
  -> keyword queue
  -> Xiaohongshu search/detail crawl
  -> quality filter
  -> Feishu feedback profile
  -> local rolling outputs
  -> fixed Feishu Base append
```

## Layers

- CLI: `scripts/xhs_cli.py` delegates to `src/xiaohongshu_scrape_posts/cli.py`.
- Rules: `src/xiaohongshu_scrape_posts/rules.py` loads the Markdown rule document.
- Quality: `src/xiaohongshu_scrape_posts/quality.py` scores and filters candidate posts.
- Feedback: `src/xiaohongshu_scrape_posts/feedback.py` reads Feishu status rows and builds a negative-feedback profile.
- Feishu: `src/xiaohongshu_scrape_posts/integrations/lark.py` appends new rows to the fixed master table.
- Legacy crawler bridge: `src/xiaohongshu_scrape_posts/crawler/legacy.py` calls maintained compatibility scripts in `work/`.

## Runtime Config

Preferred Feishu config:

```powershell
$env:XHS_LARK_BASE_DOMAIN="https://your-domain.feishu.cn"
$env:XHS_LARK_BASE_TOKEN="your_base_token"
$env:XHS_LARK_TABLE_ID="your_table_id"
```

Rule override:

```powershell
$env:INSFORGE_XHS_RULE_DOC="D:\path\to\rules.md"
```

Optional crawler profile:

```powershell
$env:XHS_BROWSER_PROFILE_DIR="C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802"
```

Private runtime state can live in:

```text
outputs/xhs_insforge_master_pointer.json
```

`outputs/` is ignored by Git.

## Commands

```powershell
python .\scripts\xhs_cli.py health
python .\scripts\xhs_cli.py rules
python .\scripts\xhs_cli.py check-login
python .\scripts\xhs_cli.py open-login --keep-open
python .\scripts\xhs_cli.py crawl --fresh --max-keywords 35 --scroll-rounds 3
python .\scripts\xhs_cli.py append --source-json outputs\your_daily_output.json --dry-run
python .\scripts\xhs_cli.py append --source-json outputs\your_daily_output.json
```

## Failure Handling

- If health checks fail, stop before crawling.
- If Xiaohongshu requires login or safety verification, open a visible login window and wait for the user.
- If Xiaohongshu reports frequent operations, stop or cool down instead of repeatedly refreshing.
- If Feishu config is missing, stop before append.
- If fewer than 25 qualified unique rows are available, report the shortfall rather than filling with low-quality posts.
