from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from enrich_xhs_profiles_and_table import write_markdown

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
INPUT_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_profiles.json"
OUTPUT_JSON = INPUT_JSON

TZ = timezone(timedelta(hours=8))
NO_CONTACT_VALUES = {"", "未发现", "获取失败", "未显示"}


def has_contact(row: dict[str, object]) -> bool:
    return str(row.get("联系方式") or "").strip() not in NO_CONTACT_VALUES


def follower_number(value: object) -> float:
    text = str(value or "").strip().replace(",", "")
    if not text or text in {"获取失败", "未显示", "-"}:
        return -1

    multipliers = {
        "k": 1_000,
        "K": 1_000,
        "w": 10_000,
        "W": 10_000,
        "万": 10_000,
        "千": 1_000,
        "m": 1_000_000,
        "M": 1_000_000,
    }
    multiplier = 1
    suffix = text[-1]
    if suffix in multipliers:
        multiplier = multipliers[suffix]
        text = text[:-1]

    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return -1
    return float(match.group(0)) * multiplier


def main() -> None:
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    rows = data["rows"]
    for index, row in enumerate(rows):
        row["_original_index"] = index
        row["_has_contact"] = has_contact(row)
        row["_followers_numeric"] = follower_number(row.get("粉丝数"))

    rows.sort(
        key=lambda row: (
            0 if row["_has_contact"] else 1,
            -float(row["_followers_numeric"]),
            int(row["_original_index"]),
        )
    )

    for row in rows:
        row.pop("_original_index", None)
        row.pop("_has_contact", None)
        row.pop("_followers_numeric", None)

    data.setdefault("meta", {})["sorted_at"] = datetime.now(TZ).isoformat()
    data["meta"]["sort_rule"] = "联系方式非空优先；各组内按粉丝数从高到低；同粉丝数保留原顺序"
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(rows)

    print(
        json.dumps(
            {
                "rows": len(rows),
                "contacts_first": sum(1 for row in rows if has_contact(row)),
                "top_10": [
                    {
                        "title": row["帖子标题"],
                        "followers": row["粉丝数"],
                        "contact": row["联系方式"],
                    }
                    for row in rows[:10]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
