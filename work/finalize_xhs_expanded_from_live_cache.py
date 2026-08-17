from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import collect_xhs_expanded_leads_with_comments as expanded
from collect_xhs_live_cache_resume import LIVE_CACHE_JSON


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    if LIVE_CACHE_JSON.exists():
        data = json.loads(LIVE_CACHE_JSON.read_text(encoding="utf-8"))
        candidates = {row["note_id"]: row for row in data.get("candidates", []) if row.get("note_id")}
        cache_meta = data.get("meta", {})
        failures = data.get("failures", [])
        source_mode = "live_cache"
    else:
        candidates = expanded.load_seed_candidates()
        cache_meta = {}
        failures = []
        source_mode = "seed_only"

    selected = expanded.classify_and_select(list(candidates.values()), expanded.TARGET)
    expanded.enrich_from_profile_cache(selected)
    audit = expanded.fill_comments(selected)
    levels: dict[str, int] = {}
    priorities: dict[str, int] = {}
    for row in selected:
        levels[row["线索等级"]] = levels.get(row["线索等级"], 0) + 1
        priorities[row["评论优先级"]] = priorities.get(row["评论优先级"], 0) + 1

    meta = {
        "generated_at": datetime.now(expanded.TZ).isoformat(),
        "window_start": expanded.SEVEN_DAY_START.isoformat(),
        "window_end": expanded.NOW.isoformat(),
        "target": expanded.TARGET,
        "row_count": len(selected),
        "keywords_count": len(expanded.KEYWORDS),
        "keywords": expanded.KEYWORDS,
        "source_mode": source_mode,
        "cache_file": str(LIVE_CACHE_JSON) if LIVE_CACHE_JSON.exists() else "",
        "cache_meta": cache_meta,
        "failures": failures,
        "filter_change": "重新纳入学习打卡、泛教程、GitHub热榜、纯工具推荐；仍剔除招聘、实习、求职、课程售卖、训练营等不适合建联内容。",
        "output_columns_removed": ["线索等级", "评论优先级", "是否直接提InsForge", "点赞", "评论", "收藏"],
        "sort_rule": "内部按线索等级/评论优先级/综合分排序；输出表不展示这些内部列。",
        "level_counts": levels,
        "priority_counts": priorities,
        "ai_flavor_audit_issues": audit,
    }
    expanded.write_outputs(selected, meta)
    print(
        json.dumps(
            {
                "rows": len(selected),
                "levels": levels,
                "priorities": priorities,
                "output_json": str(expanded.OUTPUT_JSON),
                "output_md": str(expanded.OUTPUT_MD),
                "inbox_md": meta.get("inbox_md"),
                "inbox_write_error": meta.get("inbox_write_error", ""),
                "lark_fields": str(expanded.LARK_FIELDS_JSON),
                "lark_records": str(expanded.LARK_RECORDS_JSON),
                "audit_issues": audit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
