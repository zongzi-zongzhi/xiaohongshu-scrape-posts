from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RULE_DOC_PATH = Path(r"D:\czj note\小红书 InsForge 建联线索池规则总结.md")
DEFAULT_OUTPUT_FIELDS = ["发布时间", "帖子名字", "帖子链接", "评论", "匹配关键词", "备注"]
DEFAULT_CORE_SELECTION_RULE = (
    "目标帖子像一个正在做项目的人遇到了后端、数据库、登录权限、API Key、部署、环境变量或数据保存问题，"
    "或者像一个会做项目的人明确吐槽手动配置这些后端能力太麻烦；不要抓内容号在教小白认识 AI 编程工具的帖子。"
)


@dataclass(frozen=True)
class XhsRuleDocument:
    path: Path
    exists: bool
    text: str
    high_priority_keywords: list[str]
    expansion_keywords: list[str]
    disabled_keywords: list[str]
    output_fields: list[str]
    append_min: int
    append_limit: int
    core_selection_rule: str

    @property
    def keyword_count(self) -> int:
        return len(self.high_priority_keywords) + len(self.expansion_keywords)

    def as_meta(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "high_priority_keyword_count": len(self.high_priority_keywords),
            "expansion_keyword_count": len(self.expansion_keywords),
            "disabled_keyword_count": len(self.disabled_keywords),
            "output_fields": self.output_fields,
            "append_min": self.append_min,
            "append_limit": self.append_limit,
            "core_selection_rule": self.core_selection_rule,
        }


def resolve_rule_doc_path() -> Path:
    raw = os.environ.get("INSFORGE_XHS_RULE_DOC", "").strip()
    return Path(raw) if raw else DEFAULT_RULE_DOC_PATH


def _heading_level(line: str) -> int | None:
    match = re.match(r"^(#{2,6})\s+.+\s*$", line)
    return len(match.group(1)) if match else None


def _extract_section(text: str, heading_contains: str) -> str:
    lines = text.splitlines()
    start = -1
    level = 0
    for index, line in enumerate(lines):
        current_level = _heading_level(line)
        if current_level and heading_contains in line:
            start = index + 1
            level = current_level
            break
    if start < 0:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        current_level = _heading_level(lines[index])
        if current_level and current_level <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _clean_item(value: str) -> str:
    text = value.strip().strip("`").strip()
    text = re.sub(r"[。；;，,]\s*$", "", text)
    return text.strip()


def _bullet_items(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if not match:
            continue
        item = _clean_item(match.group(1))
        if item:
            items.append(item)
    return list(dict.fromkeys(items))


def _numbered_items(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if not match:
            continue
        item = _clean_item(match.group(1))
        if item:
            items.append(item)
    return items


def _daily_count(section: str, marker: str, default: int) -> int:
    match = re.search(rf"{re.escape(marker)}\s*(\d+)\s*条", section)
    return int(match.group(1)) if match else default


def _core_selection_rule(text: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    match = re.search(
        r"这个帖子像“一个正在做项目的人遇到了后端、数据库、部署问题”，或者像“一个会做项目的人吐槽手动配置这些后端能力太麻烦”。不要抓内容号在教小白认识AI编程工具的帖子。",
        normalized,
    )
    if match:
        return (
            "这个帖子像“一个正在做项目的人遇到了后端、数据库、部署问题”，或者像“一个会做项目的人吐槽手动配置这些后端能力太麻烦”。"
            "不要抓内容号在教小白认识 AI 编程工具的帖子。"
        )
    match = re.search(
        r"目标帖子像一个正在做项目的人遇到了后端、数据库、登录权限、APIKey、部署、环境变量或数据保存问题，或者像一个会做项目的人明确吐槽手动配置这些后端能力太麻烦。不要抓内容号在教小白认识AI编程工具的帖子。",
        normalized,
    )
    if match:
        return DEFAULT_CORE_SELECTION_RULE
    return DEFAULT_CORE_SELECTION_RULE


def load_rules(path: Path | None = None) -> XhsRuleDocument:
    rule_path = path or resolve_rule_doc_path()
    exists = rule_path.exists()
    text = rule_path.read_text(encoding="utf-8") if exists else ""

    high_priority = _bullet_items(_extract_section(text, "高优先级关键词"))
    expansion = _bullet_items(_extract_section(text, "可扩展关键词"))
    disabled = _bullet_items(_extract_section(text, "禁用或低优先级关键词"))
    output_fields = _numbered_items(_extract_section(text, "输出字段规则")) or DEFAULT_OUTPUT_FIELDS
    daily_section = _extract_section(text, "每日数量规则")
    append_min = _daily_count(daily_section, "最少", 25)
    append_limit = _daily_count(daily_section, "最多", 50)

    return XhsRuleDocument(
        path=rule_path,
        exists=exists,
        text=text,
        high_priority_keywords=high_priority,
        expansion_keywords=expansion,
        disabled_keywords=disabled,
        output_fields=output_fields,
        append_min=append_min,
        append_limit=append_limit,
        core_selection_rule=_core_selection_rule(text),
    )


RULES = load_rules()
