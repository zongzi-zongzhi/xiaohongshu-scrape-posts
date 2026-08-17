import importlib.util
import json
import re
import time
from datetime import timedelta
from pathlib import Path


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
BASE_SCRIPT = ROOT / "work" / "xhs_collect_recent_cli.py"

spec = importlib.util.spec_from_file_location("recent_cli", BASE_SCRIPT)
recent = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(recent)


def load_existing(cutoff):
    records = {}
    for path in recent.RAW_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        keyword = data.get("keyword", "")
        variant = data.get("variant", {})
        for item in data.get("results", []):
            recent.add_item(records, item, keyword, variant, cutoff)
    return records


def existing_keywords():
    names = set()
    for path in recent.RAW_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("variant", {}).get("sort_by") is None and data.get("variant", {}).get("publish_time") is None:
            names.add(data.get("keyword", ""))
    return names


def run_until_full(records, cutoff):
    failures = []
    done = existing_keywords()
    variants = [
        {"sort_by": None, "publish_time": None},
        {"sort_by": "最新", "publish_time": "半年内"},
        {"sort_by": "最多评论", "publish_time": "半年内"},
        {"sort_by": "最多收藏", "publish_time": "半年内"},
        {"sort_by": "最多点赞", "publish_time": "半年内"},
    ]

    for variant_index, variant in enumerate(variants, start=1):
        print(f"resume_variant={variant_index} count={len(records)} variant={variant}", flush=True)
        for index, keyword in enumerate(recent.KEYWORDS, start=1):
            if variant_index == 1 and keyword in done:
                continue
            print(f"[{index}/{len(recent.KEYWORDS)}] {keyword}", flush=True)
            try:
                items = recent.run_search(keyword, variant)
            except Exception as exc:
                failures.append(
                    {
                        "keyword": keyword,
                        "variant": variant,
                        "error": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                time.sleep(5)
                continue

            raw_path = recent.RAW_DIR / f"resume_v{variant_index}_{recent.safe_name(keyword)}.json"
            raw_path.write_text(
                json.dumps({"keyword": keyword, "variant": variant, "results": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            for item in items:
                recent.add_item(records, item, keyword, variant, cutoff)
            print(f"two_week_count={len(records)}", flush=True)
            if len(records) >= recent.TARGET:
                return records, failures
            time.sleep(4 if index % 4 else 12)
    return records, failures


def main():
    two_week_cutoff = recent.NOW - timedelta(days=14)
    one_week_cutoff = recent.NOW - timedelta(days=7)
    records = load_existing(two_week_cutoff)
    one_week_records = load_existing(one_week_cutoff)
    print(
        json.dumps(
            {
                "existing_one_week": len(one_week_records),
                "existing_two_week": len(records),
                "two_week_cutoff": two_week_cutoff.isoformat(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    records, failures = run_until_full(records, two_week_cutoff)
    rows = recent.select_rows(records)
    meta = {
        "generated_at": recent.datetime.now(recent.TZ).isoformat(),
        "now": recent.NOW.isoformat(),
        "selection_window": "14_days" if len(rows) >= recent.TARGET else "14_days_partial",
        "one_week_cutoff": one_week_cutoff.isoformat(),
        "two_week_cutoff": two_week_cutoff.isoformat(),
        "one_week_candidate_count": len(one_week_records),
        "final_candidate_count": len(records),
        "selected_count": len(rows),
        "failures": failures,
        "keywords": recent.KEYWORDS,
        "note": "One-week public search was insufficient; two-week public search was used to fill the target. No interactions were performed.",
    }
    recent.write_outputs(rows, meta)


if __name__ == "__main__":
    main()
