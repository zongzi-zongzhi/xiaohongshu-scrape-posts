from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
OUT_DIR = ROOT / "outputs"
INBOX = Path(r"D:\czj note\00_Inbox")

SOURCE_JSON = OUT_DIR / "xhs_insforge_7day_title_body_20260721_20260727.json"
OUTPUT_JSON = OUT_DIR / "xhs_insforge_comment_examples_7day_20260721_20260727.json"
OUTPUT_MD = OUT_DIR / "xhs_insforge_comment_examples_7day_20260721_20260727.md"
INBOX_MD = INBOX / "小红书建联评论方向_7天总和版_20260721-20260727.md"

LARK_FIELDS_JSON = ROOT / "work" / "xhs_comment_base_fields.json"
LARK_RECORDS_JSON = ROOT / "work" / "xhs_comment_records_payload.json"

FIELDS = ["发布时间", "帖子名字", "帖子链接", "评论方向", "评论例子", "帖子正文部分"]

COMMENT_PLAN: dict[str, tuple[str, str]] = {
    "0基础小白vibecoding的AI APP产品【Wonder": (
        "先认可对方把真实需求做成 demo，再轻轻切到“第一批用户体验需要登录、收藏、反馈数据”这类后端承接。",
        "这个选题挺有感觉，特别是“先判断值不值得花时间”这点。后面如果要做账号、收藏、反馈这些，后端别一开始铺太重；我们在做 InsForge，也是在把登录和数据表这些先兜住，让 demo 阶段能多试几轮。",
    ),
    "vibe coding 完了，咋部署？": (
        "顺着 localhost 这个高频痛点聊，把“能本地打开”和“能让别人稳定访问”区分开，再自然带到 InsForge 的后端托底。",
        "localhost 这个太真实了，很多小白第一次都会卡这一步：自己电脑能跑，发给别人就没了。后面再加登录、数据保存，又是一层坑。我们做 InsForge 就是想把这些基础后端先打包好，前期别被部署和数据库拖住。",
    ),
    "AI写完代码就敢上线？Too young！": (
        "认同“AI 写完只是开始”，重点接住 SQL、权限、上线前检查这些风险，用 InsForge 做稳定底座。",
        "这个说到痛处了。AI 写出页面很快，SQL、权限、上线前校验才最折磨。InsForge 现在比较适合先把登录、数据表、API 这些底座放稳，再让 AI 去改前端，心里会踏实很多。",
    ),
    "Vibe Coding一点也不vibe，企业项目真会踩坑": (
        "抓住“demo 爽、交付崩”的落差，回应权限、数据状态、异常边界，再放入 InsForge 的价值。",
        "“页面跑通了，不代表逻辑没漏”这句很准。权限、数据状态、异常边界这些，AI 经常写得像样，但一交付就露馅。我们做 InsForge 也是冲这个问题来的，想让 AI 项目到后端这一步别散掉。",
    ),
    "vibecoding能搞前端，后端怎么办？": (
        "不正面碰竞品，顺着“前端越来越快、后端成卡点”的共识，温和补充 InsForge 的同类解决思路。",
        "这个卡点确实高频。现在前端出来得太快，反而显得后端更磨人：表怎么建、登录怎么做、API 怎么接。我们在做 InsForge，思路也是把这些先封好，让做 AI 小项目的人少碰后端细节。",
    ),
    "小白vibecoding踩坑记（一）": (
        "正文信息少，适合轻互动：蹲后续、认可踩坑贴价值，再顺带点出后端常见坑。",
        "蹲后续，这类踩坑贴比纯教程更有用。小白做 AI 项目很容易先盯页面，后面登录、数据保存、部署一个个冒出来。我们做 InsForge 也是想先把这些基础件铺好，少来回返工。",
    ),
    "小白AI Coding 踩过哪些坑？": (
        "围绕对方从 Coze 到 Supabase 重构登录体系的经历，强调账号、权限、部署不能随便糊。",
        "你这个从 Coze 登录到 Supabase 重构的经历太典型了。账号体系一开始看着能糊，后面出问题就得整套换。InsForge 现在把登录、数据表、API 放在一起做，就是想让小白少在这些基础坑里换方案。",
    ),
    "Vibecoding小程序踩坑复盘": (
        "接住“160 人、收益 0、留存低”的复盘点，建议尽早记录用户行为数据，再提 InsForge 适合做轻数据链路。",
        "160 人收益 0 这个复盘挺真实的。功能简单时，留存和行为数据最好早点记下来，不然后面只能靠感觉猜。InsForge 这类轻后端工具就适合先把用户、记录、反馈这些数据链路搭起来。",
    ),
    "Vibe Coding一个中型项目的心路历程": (
        "认可对方第三次才把文档、审计、架构拉起来的经验，强调中型项目需要先稳住数据和后端边界。",
        "这篇挺少见，很多人只晒 AI 写了多少代码，很少讲前两次怎么失控。中型项目里，数据结构和后端边界最好早点定住。InsForge 也是往这个方向做：先把基础后端固定下来，AI 写代码时不容易越跑越歪。",
    ),
    "单二进制Supabase兼容后端tinb": (
        "从轻量 Supabase 替代切入，和 InsForge 的“开箱可用后端”定位做自然对照。",
        "这个方向有意思，单二进制对自部署党很友好。现在很多小项目要的就是轻一点的数据库、鉴权和 API，不想一上来就背一堆运维。InsForge 也在做类似取向，只是更偏 AI 小项目开箱用。",
    ),
    "“全栈”开发过程复盘": (
        "抓住 RLS、anon 权限、Supabase 连接这些具体坑，给出“默认流程做顺”的种草点。",
        "RLS 和 anon 权限这个坑太常见了，AI 能把库连上，但权限策略一错就各种查不到。我们做 InsForge 时也很在意这块，尽量把登录、数据、API 的默认流程做顺，小项目别被配置卡太久。",
    ),
    "前端调用AI，千万别把API Key写在这里": (
        "强认同安全提醒，把 API Key 泄露和后端代理能力连接起来，突出 InsForge 让密钥留在后端。",
        "这个提醒真该贴在每个 AI 前端项目门口。很多 demo 跑得起来，key 也顺手暴露了。InsForge 的一个用处就是让前端只调该调的接口，密钥和数据权限放后端兜着，少一点裸奔风险。",
    ),
    "新手小白，如何vibe coding一款产品？": (
        "正文信息少，走通用建联：小白第一款产品常卡在页面之后的登录、数据、稳定访问。",
        "小白做第一款产品，页面出来以后才会发现后面的事更磨人：登录、数据保存、上线后别人能不能稳定打开。我们在做 InsForge，就是想把这几件事先打包好，前期验证会轻一点。",
    ),
    "数据库“能跑”和“跑得对”完全是两回事！": (
        "围绕数据质量、约束、权限回应，用 InsForge 的数据层稳定性做轻种草。",
        "数据能写进去只是第一关，后面对账、时区、并发这些才容易补刀。AI 做项目时更要早点把字段、约束和权限定住。InsForge 也在往这个方向做，先让小项目的数据层别这么脆。",
    ),
    "🔥 最近很火的开源项目：OpenShip": (
        "借 OpenShip 的基础设施打包方向，聊独立开发早期订阅费和部署心智负担，再提 InsForge 的轻后端。",
        "OpenShip 这种把常用基础设施打包的方向挺值得看。很多独立开发项目还没开始赚钱，订阅费和部署心智先压上来了。InsForge 也想把数据库、登录、API 压成一套更轻的后端，先让项目跑起来。",
    ),
    "小白如何发布第一个 Vibe Coding 产品": (
        "认可对方的发布分层思路，顺着“先验证、再接 BaaS、再自建”的节奏介绍 InsForge。",
        "这篇讲得很实在，尤其是先跑通体验、再接 BaaS、最后再考虑自建后端这个节奏。InsForge 也挺适合放在中间这层：先让项目有登录、有数据、有 API，需求真起来了再折腾复杂架构。",
    ),
}

AI_FLAVOR_PATTERNS = [
    re.compile(r"不是.+而是"),
    re.compile(r"不只是.+更是"),
    re.compile(r"真正"),
    re.compile(r"本质上"),
    re.compile(r"核心在于"),
    re.compile(r"总的来说"),
    re.compile(r"你觉得呢"),
]


def raw_url(value: str) -> str:
    text = str(value or "").strip()
    match = re.match(r"\[(https?://[^\]]+)\]\((https?://[^)]+)\)", text)
    return match.group(2) if match else text


def format_dt(value: Any) -> str:
    text = str(value or "")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text


def md_escape(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = text.replace("|", r"\|")
    return text.replace("\n", "<br>")


def audit_comment(text: str) -> list[str]:
    return [pattern.pattern for pattern in AI_FLAVOR_PATTERNS if pattern.search(text)]


def main() -> None:
    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    audit_issues: dict[str, list[str]] = {}

    for raw in source.get("rows", []):
        title = str(raw.get("帖子名字") or "").strip()
        direction, comment = COMMENT_PLAN.get(
            title,
            (
                "先回应对方具体痛点，再轻带 InsForge 能帮小项目处理登录、数据和 API。",
                "这个坑挺典型的，AI 把页面做出来只是第一段路，登录、数据和 API 往往才开始卡。我们在做 InsForge，就是想先把这块垫稳一点。",
            ),
        )
        issues = audit_comment(comment)
        if issues:
            audit_issues[title] = issues
        rows.append(
            {
                "发布时间": format_dt(raw.get("published_at")),
                "帖子名字": title,
                "帖子链接": raw_url(str(raw.get("帖子链接") or "")),
                "评论方向": direction,
                "评论例子": comment,
                "帖子正文部分": str(raw.get("帖子正文部分") or "").strip(),
            }
        )

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_base": "https://zcnvjlr35o2b.feishu.cn/base/Q71ybpUmMamG6xshZhQc9bDxnGb",
            "source_json": str(SOURCE_JSON),
            "row_count": len(rows),
            "humanizer_skill": "remove-ai-flavor",
            "ai_flavor_audit_issues": audit_issues,
        },
        "rows": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "| 发布时间 | 帖子名字 | 帖子链接 | 评论方向 | 评论例子 | 帖子正文部分 |",
        "|---:|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["发布时间"]),
                    md_escape(row["帖子名字"]),
                    f"[打开]({row['帖子链接']})",
                    md_escape(row["评论方向"]),
                    md_escape(row["评论例子"]),
                    md_escape(row["帖子正文部分"]),
                ]
            )
            + " |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    INBOX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fields = [{"name": field, "type": "text"} for field in FIELDS]
    records = {
        "fields": FIELDS,
        "rows": [[row[field] for field in FIELDS] for row in rows],
    }
    LARK_FIELDS_JSON.write_text(json.dumps(fields, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    LARK_RECORDS_JSON.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(
        json.dumps(
            {
                "rows": len(rows),
                "output_json": str(OUTPUT_JSON),
                "output_md": str(OUTPUT_MD),
                "inbox_md": str(INBOX_MD),
                "lark_fields": str(LARK_FIELDS_JSON),
                "lark_records": str(LARK_RECORDS_JSON),
                "ai_flavor_audit_issues": audit_issues,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
