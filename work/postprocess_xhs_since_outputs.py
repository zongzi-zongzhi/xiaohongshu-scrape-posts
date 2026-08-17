from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUTPUT_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.md"
OUTPUT_CSV = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_since_20260723_with_profiles.csv"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书痛点+建议评论方向_新增_20260723-20260726.md")
PROFILE_CACHE = ROOT / "outputs" / "xhs_insforge_author_profiles_cache_since_20260723.json"

TZ = timezone(timedelta(hours=8))
CONTACT_PATTERNS = [
    ("邮箱", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)),
    ("手机号", re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")),
    ("微信", re.compile(r"(?:微信|VX|vx|V信|v信|WeChat|wechat|wx|WX|加V|加v)[号：:\s]*([A-Za-z][A-Za-z0-9_-]{4,19})")),
    ("QQ", re.compile(r"(?:QQ|qq)[号：:\s]*([1-9]\d{4,11})")),
    ("公众号", re.compile(r"(?:公众号|公号|订阅号)[：:\s]*([^，。；;\n\s]{2,30})")),
]
HEADERS = ["帖子标题", "帖子链接", "点赞", "评论", "收藏", "建议评论", "帖主主页链接", "粉丝数", "联系方式"]


def md_escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")


def to_int(value: Any) -> int:
    text = "" if value is None else str(value).strip().lower().replace(",", "")
    if not text:
        return 0
    multiplier = 1
    if text.endswith(("w", "万")):
        multiplier = 10000
        text = text[:-1]
    if text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else 0


def followers_from_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text).replace("|", " "))
    for pattern in [
        r"(?<![\d.])(\d+(?:\.\d+)?\s*(?:万|w|W|k|K)?)\s*粉丝",
        r"粉丝\s*(\d+(?:\.\d+)?\s*(?:万|w|W|k|K)?)",
    ]:
        match = re.search(pattern, normalized)
        if match:
            return re.sub(r"\s+", "", match.group(1))
    return ""


def followers_from_profile(profile: dict[str, Any] | None, body_text: str) -> str:
    blob = json.dumps(profile or {}, ensure_ascii=False)
    follower_match = re.search(r'"(?:name|type)"\s*:\s*"(?:粉丝|fans)"[^{}]{0,160}?"(?:i18nCount|count)"\s*:\s*"?([^",}]+)', blob)
    if not follower_match:
        follower_match = re.search(r'"(?:i18nCount|count)"\s*:\s*"?([^",}]+)"?[^{}]{0,120}"(?:name|type)"\s*:\s*"(?:粉丝|fans)"', blob)
    if follower_match:
        return follower_match.group(1)
    return followers_from_text(body_text) or "未显示"


def profile_header_text(body_text: str) -> str:
    text = str(body_text or "")
    marker = "电话：9501-3888"
    index = text.rfind(marker)
    if index >= 0:
        text = text[index + len(marker):]
    for stop in ["\n关注\n笔记", "\n笔记\n收藏", "\nTA 还没有收藏"]:
        stop_index = text.find(stop)
        if stop_index > 0:
            text = text[:stop_index]
            break
    return text


def contact_from_text(text: str) -> str:
    lines = [line for line in str(text).splitlines() if "小红书号" not in line]
    text = "\n".join(lines)
    found: list[str] = []
    for label, pattern in CONTACT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            value = value.strip(" ：:，,。.;；")
            if label == "公众号" and len(value) > 18:
                continue
            item = f"{label}: {value}"
            if value and item not in found:
                found.append(item)
    return "；".join(found) if found else "未发现"


def has_contact(row: dict[str, Any]) -> bool:
    return bool(row.get("联系方式") and row.get("联系方式") not in {"未发现", "获取失败", ""})


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (0 if has_contact(row) else 1, -to_int(row.get("粉丝数")), -to_int(row.get("点赞"))))


def write_outputs(data: dict[str, Any]) -> None:
    rows = data["rows"]
    md_lines = [
        "| " + " | ".join(HEADERS) + " |",
        "|---|---|---:|---:|---:|---|---|---:|---|",
    ]
    for row in rows:
        md_lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row.get("帖子标题", "")),
                    f"[打开]({row.get('帖子链接', '')})",
                    str(row.get("点赞", "")),
                    str(row.get("评论", "")),
                    str(row.get("收藏", "")),
                    md_escape(row.get("建议评论", "")),
                    f"[打开]({row.get('帖主主页链接', '')})" if row.get("帖主主页链接") else "",
                    md_escape(row.get("粉丝数", "")),
                    md_escape(row.get("联系方式", "")),
                ]
            )
            + " |"
        )
    markdown = "\n".join(md_lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.write_text(markdown, encoding="utf-8")
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in HEADERS})
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    cache = json.loads(PROFILE_CACHE.read_text(encoding="utf-8"))
    for row in data["rows"]:
        record = cache.get(row.get("author_id", ""), {})
        body_text = str(record.get("body_text") or "")
        row["粉丝数"] = followers_from_profile(record.get("profile"), body_text)
        row["联系方式"] = contact_from_text(profile_header_text(body_text))
    data["rows"] = sort_rows(data["rows"])
    data.setdefault("meta", {})["postprocessed_at"] = datetime.now(TZ).isoformat()
    data["meta"]["contact_extraction_rule"] = "仅从主页头部/简介区提取联系方式；排除小红书号和历史笔记标题"
    write_outputs(data)
    print(
        json.dumps(
            {
                "rows": len(data["rows"]),
                "contacts": sum(1 for row in data["rows"] if has_contact(row)),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "output_json": str(OUTPUT_JSON),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
