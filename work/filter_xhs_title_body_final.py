from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
INPUT_JSON = ROOT / "outputs" / "xhs_insforge_since_20260723_title_body.json"
OUTPUT_JSON = ROOT / "outputs" / "xhs_insforge_since_20260723_title_body_filtered.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_since_20260723_title_body_filtered.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\小红书痛点帖子正文_新增_20260723-20260726.md")
TZ = timezone(timedelta(hours=8))

EXCLUDE_RE = re.compile(
    r"(职场那些事儿|文科转码|自由职业|副业|不想上班|搞钱|宝藏网站|必备宝藏|路演|大会|产品岗|"
    r"面试|岗位|考查点|舰队模式|头部大厂|行业反思|个人生产力|工具合集|AI视频|个人简历|"
    r"人生支线工作台|工作台|市场情绪|选题|内容创作|提示词)"
)

INCLUDE_RE = re.compile(
    r"(0基础|零基础|小白|AI APP|App|CRM|后端|数据库|API|登录|鉴权|支付|部署|上线|SQL|"
    r"项目改崩|撤回|版本|踩坑|大坑|避坑|交付|权限|数据状态|MCP|代码库记忆|搭建网站|"
    r"做网站|作品集网站|Agent)"
)


def md_escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")


def keep(row: dict[str, Any]) -> bool:
    text = f"{row.get('帖子名字', '')}\n{row.get('帖子正文部分', '')}"
    if EXCLUDE_RE.search(text):
        return False
    return bool(INCLUDE_RE.search(text))


def write_md(rows: list[dict[str, Any]]) -> None:
    lines = [
        "| 帖子链接 | 帖子名字 | 帖子正文部分 |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[打开]({row['帖子链接']})",
                    md_escape(row["帖子名字"]),
                    md_escape(row["帖子正文部分"]),
                ]
            )
            + " |"
        )
    markdown = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.write_text(markdown, encoding="utf-8")


def main() -> None:
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    rows = [row for row in data.get("rows", []) if keep(row)]
    data["rows"] = rows
    data.setdefault("meta", {})["filtered_at"] = datetime.now(TZ).isoformat()
    data["meta"]["row_count"] = len(rows)
    data["meta"]["final_filter"] = "按标题+正文保留 AI Coding 项目/后端/数据库/部署/上线/安全/踩坑相关；剔除职业、面试、路演、泛工具清单等低痛点内容"
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(rows)
    print(json.dumps({"rows": len(rows), "output_md": str(OUTPUT_MD), "inbox_md": str(INBOX_MD), "output_json": str(OUTPUT_JSON)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
