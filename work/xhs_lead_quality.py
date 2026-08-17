from __future__ import annotations

import collections
import datetime as dt
import math
import re
from typing import Any

try:
    import xhs_rules_doc
except Exception:
    xhs_rules_doc = None


FIELD_TIME = "发布时间"
FIELD_TITLE = "帖子名字"
FIELD_LINK = "帖子链接"
FIELD_KEYWORDS = "匹配关键词"

NOTE_ID_RE = re.compile(r"/(?:explore|discovery/item)/([0-9a-f]{24})")

RULES = xhs_rules_doc.RULES if xhs_rules_doc is not None else None

CORE_SELECTION_RULE_FALLBACK = (
    "目标帖子像一个正在做项目的人遇到了后端、数据库、登录权限、API Key、部署、环境变量或数据保存问题，"
    "或者像一个会做项目的人明确吐槽手动配置这些后端能力太麻烦；不要抓内容号在教小白认识 AI 编程工具的帖子。"
)
CORE_SELECTION_RULE = RULES.core_selection_rule if RULES is not None else CORE_SELECTION_RULE_FALLBACK

WORKBUDDY_KEYWORDS = [
    "workbuddy",
    "WorkBuddy",
    "WorkBuddy 踩坑",
    "WorkBuddy 后端",
    "WorkBuddy 数据库",
    "WorkBuddy 配置 麻烦",
    "WorkBuddy 数据保存",
]

HIGH_INTENT_KEYWORDS = [
    *WORKBUDDY_KEYWORDS,
    "AI 做APP 数据保存",
    "AI 做网站 数据保存",
    "AI 搭建网站 数据库",
    "AI 项目 数据库",
    "AI 项目 后端",
    "AI 项目 上线失败",
    "AI 项目 部署失败",
    "AI 项目 登录注册",
    "AI 项目 登录权限",
    "AI 项目 API Key",
    "AI 项目 环境变量",
    "AI 项目 数据存不进去",
    "AI 做 APP 后端",
    "AI 做 APP 登录权限",
    "AI 做 APP 环境变量",
    "AI 做网站 后端",
    "AI 做网站 登录权限",
    "AI 做网站 环境变量",
    "Vercel 部署失败",
    "Vercel Supabase",
    "Vercel API Key",
    "Vercel 环境变量",
    "Vercel 环境变量 麻烦",
    "Vercel 配置 麻烦",
    "Supabase auth",
    "Supabase Auth 登录",
    "Supabase RLS 权限",
    "Supabase 数据保存",
    "Supabase 配置 麻烦",
    "Supabase 手动配置",
    "Supabase 不想配置",
    "Supabase 登录权限",
    "Supabase 环境变量",
    "Supabase API Key",
    "Supabase Edge Function",
    "Supabase 小白 踩坑",
    "Supabase 踩坑",
    "Auth 配置 麻烦",
    "RLS 配置 麻烦",
    "API Key 配置 麻烦",
    "数据库 配置 麻烦",
    "后端 配置 麻烦",
    "登录权限 配置 麻烦",
    "手动配置 后端",
    "手动配置 数据库",
    "手动配置 权限",
    "手动配置 API Key",
    "不想配数据库",
    "不想配权限",
    "不想配 Supabase",
    "不想自己搭后端",
    "Firebase 后端",
    "Supabase 替代",
    "PocketBase 后端",
    "独立开发 后端",
    "独立开发 数据库",
    "独立开发 登录注册",
    "独立开发 部署失败",
    "vibe coding 后端",
    "vibe coding 数据库",
    "vibe coding 数据保存",
    "vibe coding 登录注册",
    "AI Coding 后端",
    "AI Coding 数据库",
    "AI Coding 部署失败",
    "AI Coding 登录注册",
    "AI Coding API Key",
    "AI Coding 环境变量",
    "Cursor 后端",
    "Cursor 数据库",
    "Cursor Supabase",
    "Cursor 部署失败",
    "Cursor API Key",
    "Cursor 环境变量",
    "Claude Code 后端",
    "Claude Code 数据库",
    "Claude Code Supabase",
    "Claude Code 部署失败",
    "Claude Code API Key",
    "Claude Code 环境变量",
    "Trae 后端",
    "Trae 数据库",
    "Trae 部署失败",
    "Lovable 后端",
    "Lovable 数据库",
    "Lovable Supabase",
    "Bolt 后端",
    "Bolt 数据库",
    "Bolt Supabase",
]

DEFAULT_HIGH_INTENT_KEYWORDS = HIGH_INTENT_KEYWORDS
HIGH_INTENT_KEYWORDS = (
    list(RULES.high_priority_keywords)
    if RULES is not None and RULES.high_priority_keywords
    else DEFAULT_HIGH_INTENT_KEYWORDS
)
EXPANSION_KEYWORDS = list(RULES.expansion_keywords) if RULES is not None else []

LOW_INTENT_KEYWORD_RE = re.compile(
    r"(GitHub|github|热榜|项目榜|榜单|日报|周报|资讯|工具推荐|工具清单|学习打卡|打卡|"
    r"教程|入门|手册|保姆级|howto入门|howto用AI手搓APP|入门vibecoding|小白 AI 编程 教程|"
    r"WorkBuddy 小白|AI Coding 小白|Vibe Coding 小白|Supabase 教程|Supabase 新手|"
    r"Cursor 教程|Claude Code 教程|Trae 教程|AI编程 学习打卡|vibe coding 学习打卡|"
    r"零基础|AI新手村|howto用好AI|AI工具|工具合集|开发工具|开源项目)",
    re.IGNORECASE,
)

LOW_INTENT_EXACT_KEYWORDS = {
    "AI编程",
    "AI 编程",
    "vibecoding",
    "个人开发者",
    "独立开发",
    "AI做APP",
    "AI做网站",
    "vibe coding 产品",
    "AI 编程 工具合集",
    "AI工具 推荐 编程",
    "开发工具 推荐 AI",
}
if RULES is not None:
    LOW_INTENT_EXACT_KEYWORDS.update(RULES.disabled_keywords)

JOB_RE = re.compile(
    r"(招聘|招人|热招|岗位|内推|投递|求职|面试|面经|简历|校招|秋招|春招|实习|offer|OFFER|薪资|"
    r"We'?re\s*hiring|hiring)",
    re.IGNORECASE,
)

SELLING_RE = re.compile(
    r"(训练营|课程|课代表|报名|私教|带学|带你|付费社群|资料包|免费领取|私我|进群|副业|月入|赚钱|"
    r"割韭菜|闭眼入|收藏.*资料|学习路线|零基础AI编程100讲)",
    re.IGNORECASE,
)

NEWS_LIST_RE = re.compile(
    r"(GitHub\s*热榜|github\s*热榜|GitHub热门|GitHub爆火|GitHub增量榜|开源热榜|项目榜|榜单|"
    r"排行榜|TOP\s*\d+|Top\s*\d+|日报|周报|每日AI资讯|AI资讯|热门项目|热门Skills|工具清单|工具合集)",
    re.IGNORECASE,
)

PURE_TUTORIAL_RE = re.compile(
    r"(保姆级|教程|入门|手册|指南|攻略|认识|介绍|科普|是什么|一图看懂|收藏|拿走不谢|配享太庙|"
    r"嘴对嘴|包教包会|手把手|零基础|小白必看|30s|30秒|1分钟|速成|配置清单|安装配置|"
    r"Day\s*\d+|黑马Day|打卡|学习笔记)",
    re.IGNORECASE,
)

TOOL_INTRO_RE = re.compile(
    r"(Cursor|Claude\s*Code|Trae|Codex|Copilot|Windsurf|通义灵码|文心快码|AI编程工具|AI 编程工具|"
    r"LLM|大语言模型|模型|工作流|workflow|Workflow)",
    re.IGNORECASE,
)

PROJECT_RE = re.compile(
    r"(App|APP|应用|网站|网页|Web|SaaS|MVP|产品|项目|小程序|独立开发|上线|部署|demo|Demo|原型|"
    r"做了个|做一个|做出来|搭了|搭建|开发|发布|用户|付费|后台|管理台|CRM|工具)",
    re.IGNORECASE,
)

BACKEND_RE = re.compile(
    r"(后端|数据库|数据表|数据保存|数据存|数据没|存储|Supabase|Firebase|PocketBase|Postgres|PostgreSQL|"
    r"SQL|RLS|Auth|auth|鉴权|权限|登录|注册|OAuth|API\s*Key|api\s*key|密钥|环境变量|接口|API|"
    r"服务端|server|Server|Edge\s*Function|Function|Webhook|webhook|Vercel|部署|上线|公网|域名|"
    r"403|401|500|CORS|token|Token|JWT)",
    re.IGNORECASE,
)

PAIN_RE = re.compile(
    r"(求助|请教|提问|求解|求推荐|有没有|有木有|怎么|咋办|怎么办|如何解决|救命|卡住|卡在|卡壳|"
    r"不会|不懂|搞不定|失败|翻车|踩坑|报错|bug|Bug|不生效|连不上|打不开|没反应|超时|"
    r"用不了|跑不通|崩了|出错|问题|疑问|难受|头疼|麻了|裂开|卡死)",
    re.IGNORECASE,
)

FRICTION_RE = re.compile(
    r"(麻烦|繁琐|太繁琐|太麻烦|复杂|太复杂|折腾|太折腾|烦|头大|不想配|不想配置|不想自己配|"
    r"不想自己干|不想自己搭|不想手动|懒得配|懒得配置|懒得搞|手动配置|每次都要配|反复配置|"
    r"配来配去|配置半天|配置到崩溃|权限.*麻烦|RLS.*麻烦|Auth.*麻烦|API\s*Key.*麻烦|"
    r"环境变量.*麻烦|Supabase.*麻烦|Vercel.*麻烦)",
    re.IGNORECASE,
)

FIRST_PERSON_RE = re.compile(
    r"(我|我的|自己|本人|新手|小白|第一次|刚开始|刚学|刚做|做了|写了|搭了|试了|遇到|卡了|"
    r"做不出来|不会后端|不懂后端|不懂数据库)",
    re.IGNORECASE,
)

AI_BUILD_RE = re.compile(
    r"(AI\s*Coding|AI编程|AI 编程|Vibe\s*Coding|vibe\s*coding|vibecoding|Cursor|Claude\s*Code|"
    r"Trae|Lovable|Bolt|WorkBuddy|workbuddy|AI\s*做|用AI做|零代码|低代码)",
    re.IGNORECASE,
)

IRRELEVANT_RE = re.compile(
    r"(论文|学术|文科论文|设计展示|UI展示|海报|音乐教师|海外社媒|黑客松|参赛|沙龙|活动|"
    r"个人网站～|有趣个人网站|项目太有意思|AI还能这么玩)",
    re.IGNORECASE,
)

TITLE_STRICT_EXCLUDE_RE = re.compile(
    r"(招聘|招人|热招|岗位|内推|投递|求职|面试|面经|简历|校招|实习|offer|薪资|行政伙伴|远程办公|"
    r"高嫁|女生易高嫁|剧本来看|达人合作|黑客冒充|专扫|分享一个\s*API\s*key|API\s*key.*分享|"
    r"评测不能只看|准确率|企业AI项目最常见|AI拯救世界|淘汰程序员|编程外行|神级skill|设计焦虑|"
    r"入门\d*|入门|教程|指南|安装指南|无脑版|保姆级|手把手|小白也能|不会写代码也能|不用懂代码|"
    r"从零实现|30秒|1分钟|速成|配置清单|工具合集|工具推荐|资料整理|拿走不谢|收藏|日报|周报|热榜|项目榜|榜单)",
    re.IGNORECASE,
)

TITLE_HELP_RE = re.compile(
    r"(求助|请教|怎么办|怎么解决|卡住|失败|上线失败|部署失败|报错|bug|连不上|存不进去|保存不了|"
    r"权限|RLS|Auth|登录|注册|API\s*Key|环境变量|配置.*麻烦|手动配置|不想.*配置|太麻烦|繁琐|搞不定|不会接后端|不想自己搭后端)",
    re.IGNORECASE,
)


def note_key(url: Any) -> str:
    text = str(url or "").strip()
    match = NOTE_ID_RE.search(text)
    if match:
        return match.group(1)
    return text.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def row_text(row: dict[str, Any]) -> str:
    return "\n".join(
        str(row.get(field) or "")
        for field in (
            FIELD_TITLE,
            "帖子标题",
            "title",
            "帖子正文",
            "帖子正文部分",
            "desc",
            "description",
            FIELD_KEYWORDS,
            "keyword",
            "keywords",
            "备注",
            "其他",
        )
    )


def keyword_values(row: dict[str, Any]) -> list[str]:
    raw_values: list[str] = []
    for field in (FIELD_KEYWORDS, "keyword", "keywords", "matched_keywords"):
        value = row.get(field)
        if isinstance(value, list):
            raw_values.extend(str(item).strip() for item in value if str(item).strip())
        elif value:
            raw_values.append(str(value).strip())
    values: list[str] = []
    for raw in raw_values:
        parts = [part.strip() for part in re.split(r"[,，、;；|/]+", raw) if part.strip()]
        values.extend(parts or [raw])
    return list(dict.fromkeys(values))


def _profile_stopped_keywords(profile: dict[str, Any] | None) -> set[str]:
    return {str(item).strip() for item in (profile or {}).get("stopped_keywords", []) if str(item).strip()}


def _profile_downweighted_keywords(profile: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    raw = (profile or {}).get("downweighted_keywords") or {}
    return raw if isinstance(raw, dict) else {}


def _keyword_matches(text: str, keyword: str) -> bool:
    key = keyword.strip()
    return bool(key) and key.lower() in text.lower()


def build_keyword_queue(base_keywords: list[str], profile: dict[str, Any] | None = None) -> list[str]:
    stopped = _profile_stopped_keywords(profile)
    downweighted = _profile_downweighted_keywords(profile)

    def blocked(keyword: str) -> bool:
        if keyword.strip() in LOW_INTENT_EXACT_KEYWORDS:
            return True
        if LOW_INTENT_KEYWORD_RE.search(keyword):
            return True
        return any(_keyword_matches(keyword, stopped_keyword) or _keyword_matches(stopped_keyword, keyword) for stopped_keyword in stopped)

    preferred: list[str] = []
    normal: list[str] = []
    tail: list[str] = []
    for keyword in [*HIGH_INTENT_KEYWORDS, *EXPANSION_KEYWORDS, *base_keywords]:
        keyword = str(keyword or "").strip()
        if not keyword or blocked(keyword):
            continue
        if any(_keyword_matches(keyword, stopped_keyword) or _keyword_matches(stopped_keyword, keyword) for stopped_keyword in stopped):
            continue
        if keyword in HIGH_INTENT_KEYWORDS:
            preferred.append(keyword)
        elif any(_keyword_matches(keyword, low_kw) or _keyword_matches(low_kw, keyword) for low_kw in downweighted):
            tail.append(keyword)
        else:
            normal.append(keyword)
    return list(dict.fromkeys([*preferred, *normal, *tail]))


def keyword_policy_summary(profile: dict[str, Any] | None) -> dict[str, Any]:
    profile = profile or {}
    downweighted = _profile_downweighted_keywords(profile)
    return {
        "rules_doc": RULES.as_meta() if RULES is not None else {},
        "stopped_keywords": list(_profile_stopped_keywords(profile)),
        "downweighted_keywords": {
            keyword: {
                "reduction": data.get("reduction"),
                "no_reply_rate": data.get("no_reply_rate"),
                "no_reply": data.get("no_reply"),
                "total": data.get("total"),
            }
            for keyword, data in downweighted.items()
            if isinstance(data, dict)
        },
        "observed_negative_terms": profile.get("observed_term_counts", {}),
    }


def analyze_candidate(row: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    text = row_text(row)
    title = str(row.get(FIELD_TITLE) or row.get("帖子标题") or row.get("title") or "").strip()
    keywords = keyword_values(row)
    positive: list[str] = []
    negative: list[str] = []

    note_id = note_key(row.get(FIELD_LINK) or row.get("url") or "")
    if note_id and note_id in set((profile or {}).get("no_reply_note_ids") or []):
        return {"keep": False, "reason": "exact_no_reply_note_id", "score": -999, "positive": [], "negative": ["exact_no_reply_note_id"], "level": "DROP"}

    for name, pattern in [
        ("project_context", PROJECT_RE),
        ("backend_or_data_pain", BACKEND_RE),
        ("help_or_failure_language", PAIN_RE),
        ("manual_config_friction", FRICTION_RE),
        ("first_person_builder", FIRST_PERSON_RE),
        ("ai_build_tool", AI_BUILD_RE),
    ]:
        if pattern.search(text):
            positive.append(name)

    for name, pattern in [
        ("job_or_recruiting", JOB_RE),
        ("course_or_selling", SELLING_RE),
        ("news_or_listing", NEWS_LIST_RE),
        ("pure_tutorial_or_intro", PURE_TUTORIAL_RE),
        ("tool_intro_without_project_pain", TOOL_INTRO_RE),
        ("irrelevant_topic", IRRELEVANT_RE),
    ]:
        if pattern.search(text):
            negative.append(name)

    has_project = "project_context" in positive
    has_backend = "backend_or_data_pain" in positive
    has_pain = "help_or_failure_language" in positive
    has_friction = "manual_config_friction" in positive
    has_first_person = "first_person_builder" in positive
    has_ai_tool = "ai_build_tool" in positive
    has_workbuddy = bool(re.search(r"workbuddy|WorkBuddy", text, re.IGNORECASE))
    title_has_backend = bool(BACKEND_RE.search(title))
    title_has_help = bool(TITLE_HELP_RE.search(title) or PAIN_RE.search(title) or FRICTION_RE.search(title))
    title_has_project_or_ai = bool(PROJECT_RE.search(title) or AI_BUILD_RE.search(title) or FIRST_PERSON_RE.search(title))
    strong_user_problem = has_backend and (has_pain or has_friction) and (has_project or has_ai_tool or has_first_person or has_friction)
    builder_backend = has_backend and has_project and (has_first_person or has_ai_tool)
    config_friction_lead = has_backend and has_friction and (has_project or has_ai_tool or has_first_person or "Supabase" in text or "Vercel" in text)

    if TITLE_STRICT_EXCLUDE_RE.search(title) and not (title_has_backend and title_has_help and title_has_project_or_ai):
        return {
            "keep": False,
            "reason": "strict_title_exclude_without_backend_pain",
            "score": -920,
            "positive": positive,
            "negative": [*negative, "strict_title_exclude_without_backend_pain"],
            "level": "DROP",
        }
    if not title_has_backend:
        return {
            "keep": False,
            "reason": "title_missing_backend_or_project_pain",
            "score": -780,
            "positive": positive,
            "negative": [*negative, "title_missing_backend_or_project_pain"],
            "level": "DROP",
        }
    if title_has_backend and not title_has_help and not has_first_person:
        return {
            "keep": False,
            "reason": "title_backend_signal_without_help_or_friction",
            "score": -760,
            "positive": positive,
            "negative": [*negative, "title_backend_signal_without_help_or_friction"],
            "level": "DROP",
        }

    if "job_or_recruiting" in negative:
        return {"keep": False, "reason": "job_or_recruiting", "score": -999, "positive": positive, "negative": negative, "level": "DROP"}
    if "course_or_selling" in negative:
        return {"keep": False, "reason": "course_or_selling", "score": -999, "positive": positive, "negative": negative, "level": "DROP"}
    if "news_or_listing" in negative:
        return {"keep": False, "reason": "news_or_listing", "score": -999, "positive": positive, "negative": negative, "level": "DROP"}
    if "irrelevant_topic" in negative:
        return {"keep": False, "reason": "irrelevant_topic", "score": -999, "positive": positive, "negative": negative, "level": "DROP"}
    if "pure_tutorial_or_intro" in negative and not (strong_user_problem or config_friction_lead):
        return {"keep": False, "reason": "tutorial_or_intro_without_specific_backend_pain", "score": -850, "positive": positive, "negative": negative, "level": "DROP"}
    if "tool_intro_without_project_pain" in negative and not (strong_user_problem or builder_backend or config_friction_lead):
        return {"keep": False, "reason": "tool_intro_without_project_backend_pain", "score": -800, "positive": positive, "negative": negative, "level": "DROP"}
    if not has_backend and not (has_workbuddy and has_pain):
        return {"keep": False, "reason": "missing_backend_database_or_deploy_signal", "score": -700, "positive": positive, "negative": negative, "level": "DROP"}
    if not (has_pain or has_friction or builder_backend or (has_workbuddy and has_project)):
        return {"keep": False, "reason": "missing_help_or_real_builder_context", "score": -650, "positive": positive, "negative": negative, "level": "DROP"}

    score = 0
    score += 35 if has_backend else 0
    score += 30 if has_pain else 0
    score += 28 if has_friction else 0
    score += 22 if has_project else 0
    score += 16 if has_first_person else 0
    score += 14 if has_ai_tool else 0
    score += 10 if has_workbuddy else 0
    if strong_user_problem:
        score += 36
    elif builder_backend:
        score += 20
    elif config_friction_lead:
        score += 18

    if "pure_tutorial_or_intro" in negative:
        score -= 22
    if "tool_intro_without_project_pain" in negative:
        score -= 18

    text_for_keywords = " ".join([text, *keywords])
    downweighted = _profile_downweighted_keywords(profile)
    for keyword, data in downweighted.items():
        if _keyword_matches(text_for_keywords, keyword):
            reduction = float(data.get("reduction") or 0.3)
            score -= int(40 * min(max(reduction, 0.3), 0.6))
            negative.append(f"feedback_downweighted:{keyword}")
            break

    stopped = _profile_stopped_keywords(profile)
    for keyword in stopped:
        if _keyword_matches(text_for_keywords, keyword):
            return {
                "keep": False,
                "reason": f"feedback_stopped_keyword:{keyword}",
                "score": -900,
                "positive": positive,
                "negative": [*negative, f"feedback_stopped_keyword:{keyword}"],
                "level": "DROP",
            }

    if score >= 95:
        level = "A-后端痛点/配置繁琐"
    elif score >= 70:
        level = "B-项目后端线索"
    else:
        level = "C-低优先级"

    keep = score >= 60
    return {
        "keep": keep,
        "reason": "" if keep else "score_below_threshold",
        "score": score,
        "positive": positive,
        "negative": list(dict.fromkeys(negative)),
        "level": level if keep else "DROP",
    }


def engagement(row: dict[str, Any]) -> int:
    total = 0
    for field in ("点赞", "评论", "收藏", "liked_count", "comment_count", "collected_count"):
        value = str(row.get(field) or "0")
        match = re.search(r"\d+", value.replace(",", ""))
        if match:
            total += int(match.group(0))
    return total


def _time_sort(row: dict[str, Any]) -> float:
    raw = str(row.get("published_at") or row.get(FIELD_TIME) or "")
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.timestamp()
    except Exception:
        return 0.0


def select_candidates(rows: list[dict[str, Any]], limit: int, profile: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    rejected_reasons: collections.Counter[str] = collections.Counter()
    levels: collections.Counter[str] = collections.Counter()
    for row in rows:
        analysis = analyze_candidate(row, profile)
        if not analysis["keep"]:
            rejected_reasons[str(analysis["reason"])] += 1
            continue
        copied = dict(row)
        copied["lead_quality_score"] = analysis["score"]
        copied["lead_quality_level"] = analysis["level"]
        copied["positive_features"] = analysis["positive"]
        copied["negative_features"] = analysis["negative"]
        levels[str(analysis["level"])] += 1
        accepted.append(copied)

    accepted.sort(
        key=lambda row: (
            int(row.get("lead_quality_score") or 0),
            min(30, int(math.log10(max(1, engagement(row))) * 12)),
            _time_sort(row),
        ),
        reverse=True,
    )
    selected = accepted if limit <= 0 else accepted[:limit]
    report = {
        "input_count": len(rows),
        "accepted_count": len(accepted),
        "selected_count": len(selected),
        "rejected_count": len(rows) - len(accepted),
        "rejected_reasons": dict(rejected_reasons.most_common()),
        "accepted_levels": dict(levels.most_common()),
        "selection_rule": CORE_SELECTION_RULE,
        "rules_doc": RULES.as_meta() if RULES is not None else {},
    }
    return selected, report
