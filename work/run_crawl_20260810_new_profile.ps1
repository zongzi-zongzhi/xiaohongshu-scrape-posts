$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:XHS_BROWSER_PROFILE_DIR = "C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802"

python .\work\crawl_xhs_incremental_20260809_20260810_merge_master_pointer.py --fresh --max-keywords 65 --scroll-rounds 1 --target 0 --select-limit 50 --page-wait-min 7000 --page-wait-max 11000 --scroll-wait-min 2200 --scroll-wait-max 4200 --keyword-cooldown-min 20 --keyword-cooldown-max 45
exit $LASTEXITCODE
