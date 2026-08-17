$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:XHS_BROWSER_PROFILE_DIR = "C:\Users\Administrator\.xiaohongshu\browser-data-insforge-20260802"

python .\work\crawl_xhs_incremental_20260804_20260805_merge_master_pointer.py --max-keywords 55 --scroll-rounds 3 --target 0 --select-limit 0
exit $LASTEXITCODE
