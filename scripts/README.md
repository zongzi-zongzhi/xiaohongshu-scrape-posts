# Scripts

Use `scripts/xhs_cli.py` as the public command entrypoint.

```powershell
python .\scripts\xhs_cli.py health
python .\scripts\xhs_cli.py rules
python .\scripts\xhs_cli.py check-login
python .\scripts\xhs_cli.py open-login --keep-open
python .\scripts\xhs_cli.py crawl --fresh --max-keywords 35 --scroll-rounds 3
python .\scripts\xhs_cli.py append --source-json outputs\your_daily_output.json --dry-run
```

The CLI imports code from `src/xiaohongshu_scrape_posts/` and calls the maintained compatibility scripts in `work/` only where the current crawler still depends on historical logic.
