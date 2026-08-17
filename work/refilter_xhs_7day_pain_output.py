from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
INBOX = Path(r"D:\czj note\00_Inbox")

INPUT_JSON = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.json"
INPUT_MD = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.md"
RAW_JSON = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727_broad_raw.json"
RAW_MD = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727_broad_raw.md"

OUTPUT_JSON = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.json"
OUTPUT_MD = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.md"
NEW_ONLY_JSON = OUT_DIR / "xhs_insforge_title_body_new_20260726_20260727.json"
INBOX_MD = INBOX / "小红书痛点帖子正文_7天总和版_20260721-20260727.md"
INBOX_NEW_MD = INBOX / "小红书痛点帖子正文_新增_20260726-20260727.md"

TZ = timezone(timedelta(hours=8))
YESTERDAY_START = datetime(2026, 7, 26, tzinfo=TZ)

HARD_EXCLUDE_RE = re.compile(
    r"(实习|实习生|招聘|招人|招募|招生|内推|校招|社招|秋招|春招|求职|简历|面试|岗位|找工作|"
    r"被裁|上岸|薪资|工资|应届|跳槽|外包|训练营|公开课|体验课|报名|学员|报班|课程|课：|"
    r"学习路线|landing清单|暑期打卡|学习打卡|每日八股|开发每日八股|八股|Day\d+|day\s*\d+|"
    r"日报|行业日报|行业要闻|热门产品|论文摘要|今日热榜|GitHub热门|GitHub AI Top|开源项目Top|"
    r"Product Hunt|收购|融资|大会|线下|直播|专场|快讯|周报|科研|论文|医疗实验室|"
    r"保姆级|教程|手册|资料大全|资料模型|专项实战题|PM必备|一张图看懂|技术栈地图|"
    r"工具合集|工具推荐|提示词|选题荒|内容创作|个人成长|市场情绪|自由职业|副业|搞钱|不想上班)"
    ,
    re.IGNORECASE,
)
TITLE_HARD_EXCLUDE_RE = re.compile(
    r"(无限弹药|数据库分析|设计师视角|同屏改\s*Markdown|算法研究|请点进来|有偿访谈|Agent落地铁三角|"
    r"财报分析|MCP 到底有什么用|摄影作品网站|联网搜索|假成绩单|手搓一个完整App|拆解AI Coding|"
    r"长期记忆库|工具链|游戏的本质|负载均衡|今日热榜|热门项目|科研必备|每日八股|学习打卡|"
    r"第\d+天|第\d+课|学习ai|学习AI|生成完整登录页面|一张图|AI Agent开源项目|怎么工作的|到底是什么)",
    re.IGNORECASE,
)
TITLE_KEEP_RE = re.compile(
    r"(小白.*vibe|新手小白.*vibe|0基础.*vibe|零基础.*AI.*做|AI\s*Coding.*踩|小白AI.*踩|"
    r"vibe\s*coding.*部署|咋部署|怎么部署|AI写完代码.*上线|企业项目.*踩坑|"
    r"vibecoding.*后端怎么办|能搞前端.*后端怎么办|vibecoding.*踩坑|小程序踩坑复盘|"
    r"Supabase.*后端|Supabase.*兼容|OpenShip|API\s*Key|密钥|数据库.*能跑|数据库.*跑得对|"
    r"Vibe Coding.*产品|发布第一个 Vibe Coding 产品|全栈.*复盘|中型项目.*心路历程)",
    re.IGNORECASE,
)

AI_BUILD_RE = re.compile(
    r"(AI\s*Coding|AI编程|AICoding|vibe\s*coding|vibecoding|Cursor|Codex|Claude|AI\s*做|AI产品|"
    r"小白|新手|零基础|0基础|独立开发|MVP|APP|App|小程序|网站|产品)",
    re.IGNORECASE,
)
BACKEND_RE = re.compile(
    r"(Supabase|后端|数据库|登录|鉴权|权限|RLS|API|接口|密钥|Key|部署|上线|云端|服务器|存储|"
    r"向量数据库|RAG|MCP)",
    re.IGNORECASE,
)
PAIN_RE = re.compile(
    r"(踩坑|避坑|翻车|卡住|报错|失败|崩溃|困境|坑|问题|复盘|怎么办|咋部署|怎么部署|"
    r"不会|搞不懂|千万别|盗用|泄露|安全|权限|登录|鉴权|上线|部署|复杂|风险|成本|慢|"
    r"数据校验|脏数据|不一致)",
    re.IGNORECASE,
)
TUTORIAL_SOFT_RE = re.compile(r"(分享|指南|经验|知识点|入门|必学|拆解|全流程|怎么工作的|到底是什么|工具链)", re.IGNORECASE)


def parse_dt(value: Any) -> datetime:
    text = str(value or "").replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt.astimezone(TZ)


def format_dt(value: Any) -> str:
    try:
        return parse_dt(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def md_escape(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = text.replace("|", r"\|")
    return text.replace("\n", "<br>")


def relevance_score(row: dict[str, Any]) -> int:
    text = f"{row.get('帖子名字', '')}\n{row.get('帖子正文部分', '')}"
    title = str(row.get("帖子名字", ""))
    if HARD_EXCLUDE_RE.search(text):
        return -100

    has_ai_build = bool(AI_BUILD_RE.search(text))
    has_backend = bool(BACKEND_RE.search(text))
    has_pain = bool(PAIN_RE.search(text))
    has_supabase = bool(re.search(r"Supabase", text, re.IGNORECASE))

    score = 0
    if has_supabase:
        score += 4
    if has_backend:
        score += 3
    if has_pain:
        score += 3
    if has_ai_build:
        score += 2
    if re.search(r"(小白|新手|零基础|0基础)", text):
        score += 2
    if re.search(r"(踩坑|避坑|翻车|复盘|怎么办|咋部署|API\s*Key|密钥|权限|登录|鉴权)", title, re.IGNORECASE):
        score += 3
    if TUTORIAL_SOFT_RE.search(title) and not re.search(r"(踩坑|避坑|复盘|怎么办|咋部署|后端|数据库|Supabase|登录|权限|上线|部署)", title, re.IGNORECASE):
        score -= 2

    if has_supabase and has_backend:
        score += 1
    if has_ai_build and has_backend and has_pain:
        score += 2
    return score


def keep_row(row: dict[str, Any]) -> bool:
    text = f"{row.get('帖子名字', '')}\n{row.get('帖子正文部分', '')}"
    title = str(row.get("帖子名字", ""))
    if TITLE_HARD_EXCLUDE_RE.search(title):
        return False
    score = relevance_score(row)
    title_fits = bool(TITLE_KEEP_RE.search(title))
    if not title_fits and score < 9:
        return False

    has_ai_build = bool(AI_BUILD_RE.search(text))
    has_backend = bool(BACKEND_RE.search(text))
    has_pain = bool(PAIN_RE.search(text))
    has_supabase = bool(re.search(r"Supabase", text, re.IGNORECASE))

    if title_fits:
        return has_backend or has_ai_build or has_supabase
    return (has_pain and (has_backend or has_ai_build)) or (has_supabase and (has_backend or has_ai_build))


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "| 发布时间 | 帖子链接 | 帖子名字 | 帖子正文部分 |",
        "|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    format_dt(row.get("published_at")),
                    f"[打开]({row['帖子链接']})",
                    md_escape(row.get("帖子名字")),
                    md_escape(row.get("帖子正文部分")),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not RAW_JSON.exists():
        shutil.copy2(INPUT_JSON, RAW_JSON)
    if INPUT_MD.exists() and not RAW_MD.exists():
        shutil.copy2(INPUT_MD, RAW_MD)

    source_json = RAW_JSON if RAW_JSON.exists() else INPUT_JSON
    payload = json.loads(source_json.read_text(encoding="utf-8"))
    raw_rows = list(payload.get("rows", []))
    rows = [row for row in raw_rows if keep_row(row)]
    rows.sort(key=lambda row: parse_dt(row.get("published_at")), reverse=True)
    new_only = [row for row in rows if parse_dt(row.get("published_at")) >= YESTERDAY_START]

    meta = dict(payload.get("meta", {}))
    meta.update(
        {
            "refiltered_at": datetime.now(TZ).isoformat(),
            "raw_row_count": len(raw_rows),
            "row_count": len(rows),
            "new_window_row_count": len(new_only),
            "quality_filter": "InsForge outreach pain posts: AI coding/vibe coding/backend/database/auth/deploy issues; excludes jobs, courses, news, hot lists, check-ins, and generic tutorials.",
            "sort_rule": "published_at desc",
            "columns": ["发布时间", "帖子链接", "帖子名字", "帖子正文部分"],
        }
    )

    final_payload = {"meta": meta, "rows": rows}
    OUTPUT_JSON.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    NEW_ONLY_JSON.write_text(json.dumps({"meta": meta, "rows": new_only}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(OUTPUT_MD, rows)
    write_markdown(INBOX_MD, rows)
    write_markdown(INBOX_NEW_MD, new_only)

    print(
        json.dumps(
            {
                "raw_rows": len(raw_rows),
                "rows": len(rows),
                "new_window_rows": len(new_only),
                "inbox_md": str(INBOX_MD),
                "new_inbox_md": str(INBOX_NEW_MD),
                "raw_backup": str(RAW_JSON),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
