from __future__ import annotations

import json
import sys
from datetime import datetime

import collect_xhs_expanded_leads_with_comments as expanded


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    candidates = expanded.load_seed_candidates()
    preselected = expanded.classify_and_select(list(candidates.values()), expanded.TARGET)
    expanded.enrich_from_profile_cache(preselected)
    audit = expanded.fill_comments(preselected)
    levels: dict[str, int] = {}
    priorities: dict[str, int] = {}
    for row in preselected:
        levels[row["线索等级"]] = levels.get(row["线索等级"], 0) + 1
        priorities[row["评论优先级"]] = priorities.get(row["评论优先级"], 0) + 1

    meta = {
        "generated_at": datetime.now(expanded.TZ).isoformat(),
        "window_start": expanded.SEVEN_DAY_START.isoformat(),
        "window_end": expanded.NOW.isoformat(),
        "target": expanded.TARGET,
        "row_count": len(preselected),
        "keywords_count": len(expanded.KEYWORDS),
        "keywords": expanded.KEYWORDS,
        "seed_files": [str(path) for path in expanded.SEED_FILES if path.exists()],
        "filter_change": "重新纳入学习打卡、泛教程、GitHub热榜、纯工具推荐；仍剔除招聘、实习、求职、课程售卖、训练营等不适合建联内容。",
        "sort_rule": "线索等级 A/B/C；同级按评论优先级、综合分、发布时间倒序",
        "finalize_mode": "live crawler stalled while fetching note details; this file was finalized from persisted seed datasets and available body/summary fields.",
        "product_basis": "InsForge 官网定位为 agent-native cloud infrastructure，包含 authentication、database、storage、edge functions、model gateway、realtime 等能力。",
        "level_counts": levels,
        "priority_counts": priorities,
        "ai_flavor_audit_issues": audit,
    }
    expanded.write_outputs(preselected, meta)
    print(
        json.dumps(
            {
                "rows": len(preselected),
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
