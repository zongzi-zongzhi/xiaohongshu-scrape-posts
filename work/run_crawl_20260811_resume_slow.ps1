$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:XHS_BROWSER_PROFILE_DIR = "C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802"

python .\work\crawl_xhs_incremental_20260810_20260811_merge_master_pointer.py --max-keywords 65 --scroll-rounds 1 --target 0 --select-limit 50 --page-wait-min 9000 --page-wait-max 14000 --scroll-wait-min 2800 --scroll-wait-max 5200 --keyword-cooldown-min 35 --keyword-cooldown-max 70
exit $LASTEXITCODE
