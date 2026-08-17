from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

import collect_xhs_expanded_leads_with_comments as expanded
import collect_xhs_since_last_crawl as base
from collect_xhs_since_title_body import extract_detail


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
WORK_DIR = ROOT / "work"
INBOX = Path(r"D:\czj note\00_Inbox")
CURRENT_OUTPUTS = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-30\insforge-xhs-daily-crawl-handoff\outputs")

START_LABEL = "20260722"
END_LABEL = "20260731"

SOURCE_JSON = OUT_DIR / f"xhs_insforge_all_crawled_posts_master_{START_LABEL}_{END_LABEL}.json"
OUT_JSON = OUT_DIR / f"xhs_insforge_all_crawled_posts_clean_body_comments_{START_LABEL}_{END_LABEL}.json"
OUT_MD = OUT_DIR / f"xhs_insforge_all_crawled_posts_clean_body_comments_{START_LABEL}_{END_LABEL}.md"
INBOX_MD = INBOX / f"小红书InsForge_所有爬取帖子总表_精简正文评论_{START_LABEL}-{END_LABEL}.md"
FIELDS_JSON = WORK_DIR / f"xhs_all_crawled_posts_clean_body_comments_base_fields_{START_LABEL}_{END_LABEL}.json"
RECORDS_JSON = WORK_DIR / f"xhs_all_crawled_posts_clean_body_comments_records_payload_{START_LABEL}_{END_LABEL}.json"
CACHE_JSON = WORK_DIR / f"xhs_all_crawled_posts_detail_cache_{START_LABEL}_{END_LABEL}.json"
VERIFY_STATE_JSON = WORK_DIR / f"xhs_all_crawled_posts_detail_verify_required_{START_LABEL}_{END_LABEL}.json"
VERIFY_SCREENSHOT = WORK_DIR / f"xhs_all_crawled_posts_detail_verify_required_{START_LABEL}_{END_LABEL}.png"

TZ = timezone(timedelta(hours=8))
NOTE_RE = re.compile(r"/explore/([0-9a-f]{24})")

FIELDS = ["发布时间", "帖子名字", "帖子链接", "帖子正文", "评论", "评论例子", "匹配关键词"]

BODY_KEYS = ["帖子正文", "帖子正文部分", "body", "desc", "description", "note_desc", "content", "正文", "text"]
COMMENT_KEYS = ["评论例子", "建议评论", "comment_example", "suggested_comment"]
TITLE_KEYS = ["帖子名字", "帖子标题", "title", "displayTitle", "display_title"]
URL_KEYS = ["帖子链接", "url", "link"]
KEYWORD_KEYS = ["匹配关键词", "matched_keywords", "keyword", "variants"]

SKIP_SOURCE_PARTS = [
    "author_profiles_cache",
    "master_pointer",
    "lark_base",
    "records_payload",
    "base_fields",
]

AI_FLAVOR_PATTERNS = [
    re.compile(r"不是.+而是"),
    re.compile(r"不只是.+更是"),
    re.compile(r"本质上"),
    re.compile(r"核心在于"),
    re.compile(r"总的来说"),
    re.compile(r"真正"),
    re.compile(r"底层逻辑"),
]


COMMENT_POOLS = {
    "security": [
        "这个提醒挺及时的。AI 写 demo 很容易把 key 顺手放前端，后面再补权限就麻烦。InsForge 把登录、数据库、函数收在后端侧，至少能少一点裸奔风险。",
        "密钥这块真得早一点想清楚。项目一旦发出去，前端里的 key 和权限配置就很难补救。InsForge 这类后端底座，适合先把敏感逻辑留在服务端。",
        "很多小项目翻车就是从 key 和权限开始的。InsForge 想把模型调用、数据库和函数放到受控的后端里，省得 demo 一上线就开始补洞。",
    ],
    "supabase": [
        "Supabase 好用，但 Auth、RLS、Functions 串起来对新手还是有点硬。InsForge 也在补这段路，让 AI 项目接数据库和鉴权时少绕几圈。",
        "这个坑很常见，表能建起来只是第一步，权限和登录才容易卡。InsForge 想把 Postgres、Auth、函数这些放进同一套工作流里。",
        "看到 Supabase 相关的坑就很有共鸣。InsForge 做的也是云后端，只是更偏给 coding agent 用，让数据库、登录和 API 别散成一地配置。",
    ],
    "database": [
        "前端跑起来以后，数据表怎么设计、接口怎么接，马上就会变成真问题。InsForge 想先把 Postgres、权限和函数这几块接稳一点。",
        "AI 写页面很快，数据一落库就开始考验工程细节。InsForge 这边也在做类似的基础能力，让小项目别卡在数据库和 API 上。",
        "这个场景挺典型的。页面能看不代表产品能用，数据保存、权限、接口都得跟上。InsForge 想让这些后端能力对 AI 更顺手。",
    ],
    "backend": [
        "后端这块很容易被低估。AI 能把代码写出来，但环境、接口、权限没接好，项目还是跑不稳。InsForge 就是想把这段后端工作接住。",
        "这个判断挺实在的。AI Coding 到最后经常卡在后端资源怎么配、API 怎么管。InsForge 现在主要就在补这块。",
        "前端 demo 越快，后端短板越明显。InsForge 想让 coding agent 直接用上数据库、登录、存储和函数，少一点手工拼接。",
    ],
    "deploy": [
        "本地能跑和别人能访问，中间差得真不少。部署、环境变量、数据库、登录一串起来就容易乱。InsForge 想让这几件事别分散在各处。",
        "上线这一步太容易卡人了，尤其是小白用 AI 做项目。InsForge 的方向是让 agent 不只写页面，也能接好后端和部署。",
        "这个坑很多人都踩过：localhost 看着没问题，一到真实访问就露馅。InsForge 想把数据、鉴权、函数和部署放到一条更顺的线上。",
    ],
    "beginner": [
        "这个对新手挺友好。真做项目时，页面之后最容易卡在登录、数据库、部署这些地方。InsForge 也在想办法把这一步做轻一点。",
        "小白用 AI 做东西，最怕前面很顺，后面被后端配置劝退。InsForge 想把数据库、Auth、函数这些变成 agent 能直接处理的能力。",
        "这种入门内容很适合收藏。等开始做自己的项目，登录、数据保存、上线这些就会冒出来，InsForge 正好在补这段空白。",
    ],
    "tool": [
        "这类工具清单值得顺着基础设施再挖一层。AI 写代码之外，数据库、权限、部署这些也得有人接。InsForge 更偏这个方向。",
        "收藏了，这种列表很适合慢慢试。现在 AI 编程工具不少，但项目真要给别人用，后端和部署还是绕不开，InsForge 就在做这块。",
        "工具越来越多，下一步要看谁能把项目带到可运行、可维护。InsForge 关注的就是数据库、Auth、函数和部署这些落地环节。",
    ],
    "agent": [
        "Agent 真能干活以后，后端上下文会变得很重要。数据库、鉴权、工具调用、部署都得接得上，InsForge 就是围着这件事在做。",
        "AI 工具越强，基础设施越不能掉链子。InsForge 想让 coding agent 直接操作云后端，别只停在生成代码这一步。",
        "这个方向很值得继续看。Agent 写代码之外，还得能稳稳接上数据库、权限和部署，InsForge 现在做的就是这类底座能力。",
    ],
    "product": [
        "独立开发最磨人的往往是后半段：账户、数据、部署、API。InsForge 想把这些后端能力给 AI 项目先铺好一点。",
        "从 demo 到能给别人用，中间差的通常不是页面，而是数据、登录和部署。InsForge 做的就是帮 AI 小项目补上这段路。",
        "这个很像真实产品会遇到的问题。AI 能加速第一版，后端和上线还得稳住，InsForge 的定位正好偏这块。",
    ],
    "general": [
        "这个点挺适合继续拆。AI 项目做得快是一回事，数据、登录、API、部署能不能稳住，又是另一回事。InsForge 主要就在补这段。",
        "有共鸣。现在 AI 写代码已经很快了，但项目要真正能用，后端和部署还是绕不开。InsForge 想让这一步更顺一点。",
        "这个观察挺实在。很多 AI 小项目第一版很快，后面卡在数据和权限上。InsForge 做的就是让这些基础能力更容易被 agent 接上。",
    ],
}


def note_id_from_url(value: Any) -> str:
    match = NOTE_RE.search(str(value or ""))
    return match.group(1) if match else ""


def xsec_token_from_url(value: Any) -> str:
    parsed = urlparse(str(value or ""))
    return (parse_qs(parsed.query).get("xsec_token") or [""])[0]


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def first_text(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, list):
            value = " ".join(str(item).strip() for item in value if str(item).strip())
        text = normalize_text(value)
        if text:
            return text
    return ""


def merge_keywords(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        else:
            parts.extend(str(item).strip() for item in str(value or "").replace(";", " ").split() if str(item).strip())
    return " ".join(list(dict.fromkeys(parts))[:32])


def iter_post_rows(obj: Any):
    if isinstance(obj, dict):
        if any(key in obj for key in ["note_id", "id", *URL_KEYS, *TITLE_KEYS, *BODY_KEYS, *COMMENT_KEYS]):
            yield obj
        for key in ("rows", "posts", "records", "items", "data"):
            value = obj.get(key)
            if isinstance(value, list):
                for item in value:
                    yield from iter_post_rows(item)
        candidates = obj.get("candidates")
        if isinstance(candidates, list):
            for item in candidates:
                yield from iter_post_rows(item)
        elif isinstance(candidates, dict):
            for key, value in candidates.items():
                if isinstance(value, dict):
                    copied = dict(value)
                    if NOTE_RE.fullmatch(str(key)):
                        copied.setdefault("note_id", key)
                    yield from iter_post_rows(copied)
        for key, value in obj.items():
            if NOTE_RE.fullmatch(str(key)) and isinstance(value, dict):
                copied = dict(value)
                copied.setdefault("note_id", key)
                yield copied
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_post_rows(item)


def build_local_maps() -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    body_map: dict[str, tuple[str, str]] = {}
    comment_map: dict[str, tuple[str, str]] = {}
    title_map: dict[str, tuple[str, str]] = {}
    for folder in (OUT_DIR, WORK_DIR):
        for path in sorted(folder.glob("*.json")):
            if any(part in path.name for part in SKIP_SOURCE_PARTS):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for row in iter_post_rows(data):
                url = first_text(row, URL_KEYS)
                note_id = first_text(row, ["note_id", "id"]) or note_id_from_url(url)
                if not note_id:
                    continue
                body = first_text(row, BODY_KEYS)
                if body and (note_id not in body_map or len(body) > len(body_map[note_id][0])):
                    body_map[note_id] = (body, path.name)
                comment = first_text(row, COMMENT_KEYS)
                if comment and (note_id not in comment_map or len(comment) > len(comment_map[note_id][0])):
                    comment_map[note_id] = (comment, path.name)
                title = first_text(row, TITLE_KEYS)
                if title and (note_id not in title_map or len(title) > len(title_map[note_id][0])):
                    title_map[note_id] = (title, path.name)
    return body_map, comment_map, title_map


def note_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    note = detail.get("note")
    if isinstance(note, dict):
        return note
    note_detail = detail.get("noteDetail") or detail.get("note_detail")
    if isinstance(note_detail, dict):
        note = note_detail.get("note")
        if isinstance(note, dict):
            return note
    note_card = detail.get("noteCard") or detail.get("note_card")
    if isinstance(note_card, dict):
        return note_card
    return detail


def is_verify_text(text: str) -> bool:
    return any(marker in str(text or "") for marker in ["扫码验证身份", "保护账号安全", "安全验证", "拖动滑块", "请完成验证"])


def load_cache() -> dict[str, dict[str, str]]:
    if not CACHE_JSON.exists():
        return {}
    try:
        data = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(data, dict):
        return {str(key): value for key, value in data.items() if isinstance(value, dict)}
    return {}


def save_cache(cache: dict[str, dict[str, str]]) -> None:
    CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_verify(page, row: dict[str, Any], processed: int, remaining: int) -> None:
    try:
        page.screenshot(path=str(VERIFY_SCREENSHOT), full_page=True)
    except Exception:
        pass
    VERIFY_STATE_JSON.write_text(
        json.dumps(
            {
                "status": "verify_required",
                "url": page.url,
                "note_id": row.get("note_id", ""),
                "title": row.get("帖子名字", ""),
                "processed_live": processed,
                "remaining_live": remaining,
                "screenshot": str(VERIFY_SCREENSHOT),
                "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def detail_from_page(page, row: dict[str, Any]) -> dict[str, str]:
    detail = extract_detail(page, {"note_id": row.get("note_id", ""), "帖子标题": row.get("帖子名字", ""), "desc": row.get("帖子正文", "")})
    title = normalize_text(detail.get("title") or row.get("帖子名字") or "")
    body = normalize_text(detail.get("body") or row.get("帖子正文") or "")
    source = normalize_text(detail.get("source") or "detail")
    return {"title": title, "body": body, "source": source}


def fetch_live_bodies(
    rows: list[dict[str, Any]],
    *,
    limit: int | None,
    sleep_min: float,
    sleep_max: float,
    page_wait_min: int,
    page_wait_max: int,
    cooldown_every: int,
    cooldown_min: float,
    cooldown_max: float,
) -> tuple[int, int, bool]:
    cache = load_cache()
    pending: list[dict[str, Any]] = []
    for row in rows:
        if normalize_text(row.get("帖子正文")):
            continue
        note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or "")
        cached = cache.get(note_id)
        if cached and normalize_text(cached.get("body")):
            row["帖子正文"] = normalize_text(cached.get("body"))
            if cached.get("title"):
                row["帖子名字"] = normalize_text(cached.get("title"))
            continue
        pending.append(row)

    if limit is not None:
        pending = pending[:limit]
    if not pending:
        return 0, 0, False

    live_filled = 0
    live_empty_or_error = 0
    verify_required = False

    with sync_playwright() as p:
        context = expanded.browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(45000)
        try:
            for index, row in enumerate(pending, start=1):
                note_id = str(row.get("note_id") or note_id_from_url(row.get("帖子链接")) or "")
                row["note_id"] = note_id
                print(f"detail_all [{index}/{len(pending)}] {note_id} {row.get('帖子名字', '')}", flush=True)
                try:
                    page.goto(row["帖子链接"], wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(random.randint(page_wait_min, page_wait_max))
                    base.dismiss_login_popup(page)
                    visible = page.evaluate("() => document.body.innerText.slice(0, 1800)")
                    if is_verify_text(visible):
                        capture_verify(page, row, index - 1, len(pending) - index + 1)
                        verify_required = True
                        break
                    if "请求太频繁" in visible:
                        cache[note_id] = {
                            "body": "",
                            "title": normalize_text(row.get("帖子名字")),
                            "status": "too_frequent",
                            "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
                        }
                        live_empty_or_error += 1
                        save_cache(cache)
                        time.sleep(45)
                        continue
                    detail = detail_from_page(page, row)
                    if detail["body"]:
                        row["帖子正文"] = detail["body"]
                        row["帖子名字"] = detail["title"] or row.get("帖子名字", "")
                        row["_body_source"] = detail["source"]
                        cache[note_id] = {
                            "body": row["帖子正文"],
                            "title": row["帖子名字"],
                            "status": detail["source"],
                            "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
                        }
                        live_filled += 1
                    else:
                        cache[note_id] = {
                            "body": "",
                            "title": normalize_text(row.get("帖子名字")),
                            "status": "live_empty",
                            "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
                        }
                        live_empty_or_error += 1
                    save_cache(cache)
                except Exception as exc:
                    cache[note_id] = {
                        "body": "",
                        "title": normalize_text(row.get("帖子名字")),
                        "status": f"live_error:{type(exc).__name__}",
                        "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
                    }
                    live_empty_or_error += 1
                    save_cache(cache)
                    print(f"detail_all_error {note_id}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                if cooldown_every > 0 and index % cooldown_every == 0:
                    time.sleep(random.uniform(cooldown_min, cooldown_max))
                else:
                    time.sleep(random.uniform(sleep_min, sleep_max))
        finally:
            context.close()

    return live_filled, live_empty_or_error, verify_required


def comment_category(row: dict[str, Any]) -> str:
    text = f"{row.get('帖子名字', '')}\n{row.get('帖子正文', '')}\n{row.get('匹配关键词', '')}".lower()
    if any(term in text for term in ["api key", "密钥", "泄露", "安全", "环境变量"]):
        return "security"
    if any(term in text for term in ["supabase", "firebase", "rls", "anon", "auth", "pocketbase", "appwrite"]):
        return "supabase"
    if any(term in text for term in ["数据库", "数据保存", "数据表", "postgres", "sql", "storage"]):
        return "database"
    if any(term in text for term in ["后端", "api", "接口", "server", "function", "函数"]):
        return "backend"
    if any(term in text for term in ["vercel", "部署", "上线", "发布", "localhost", "公网", "域名"]):
        return "deploy"
    if any(term in text for term in ["教程", "入门", "学习", "打卡", "小白", "新手", "零基础"]):
        return "beginner"
    if any(term in text for term in ["github", "热榜", "开源项目", "工具推荐", "工具合集", "清单", "盘点"]):
        return "tool"
    if any(term in text for term in ["agent", "mcp", "cursor", "claude", "trae", "codex", "vibe"]):
        return "agent"
    if any(term in text for term in ["独立开发", "产品", "mvp", "创业", "app", "小程序", "网站"]):
        return "product"
    return "general"


def de_ai_comment(text: str) -> str:
    value = normalize_text(text)
    value = value.replace("我们做 InsForge 时也", "InsForge 这边也")
    value = value.replace("我们做 InsForge", "InsForge")
    value = value.replace("本质上", "")
    value = value.replace("核心在于", "")
    value = value.replace("总的来说，", "")
    value = value.replace("真正", "")
    value = re.sub(r"这不是(.{1,24})，而是(.{1,36})。", r"\2。", value)
    value = re.sub(r"不是(.{1,20})而是", r"\1之外，也要看", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def make_comment(row: dict[str, Any], index: int) -> str:
    category = comment_category(row)
    pool = COMMENT_POOLS[category]
    seed = str(row.get("note_id") or row.get("帖子链接") or index)
    picked = pool[(sum(ord(ch) for ch in seed) + index) % len(pool)]
    candidate = de_ai_comment(picked)
    if not any(pattern.search(candidate) for pattern in AI_FLAVOR_PATTERNS):
        return candidate

    temp = {
        "note_id": row.get("note_id", ""),
        "published_at": row.get("发布时间", ""),
        "帖子名字": row.get("帖子名字", ""),
        "帖子链接": row.get("帖子链接", ""),
        "帖子正文部分": row.get("帖子正文", ""),
        "匹配关键词": row.get("匹配关键词", ""),
    }
    level, priority, mention = expanded.classify(temp)
    temp["线索等级"] = "C-轻互动" if level == "DROP" else level
    temp["评论优先级"] = priority or "P3"
    temp["是否直接提InsForge"] = mention or "先不提，等回复"
    _, generated = expanded.comment_plan(temp)
    return de_ai_comment(generated)


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def load_rows() -> list[dict[str, Any]]:
    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    source_rows = [row for row in data.get("rows", []) if isinstance(row, dict)]
    body_map, comment_map, title_map = build_local_maps()

    rows: list[dict[str, Any]] = []
    for row in source_rows:
        url = first_text(row, URL_KEYS)
        note_id = first_text(row, ["note_id", "id"]) or note_id_from_url(url)
        title = first_text(row, TITLE_KEYS)
        body = first_text(row, BODY_KEYS)
        comment = first_text(row, COMMENT_KEYS)
        keywords = merge_keywords(*(row.get(key) for key in KEYWORD_KEYS))
        if note_id:
            if not title and note_id in title_map:
                title = title_map[note_id][0]
            if not body and note_id in body_map:
                body = body_map[note_id][0]
            if not comment and note_id in comment_map:
                comment = comment_map[note_id][0]
        rows.append(
            {
                "发布时间": first_text(row, ["发布时间", "published_at", "publish_time", "created_at"]),
                "帖子名字": title,
                "帖子链接": url,
                "帖子正文": body,
                "评论": "",
                "评论例子": de_ai_comment(comment),
                "匹配关键词": keywords,
                "note_id": note_id,
            }
        )
    rows.sort(key=lambda item: expanded.parse_dt(item.get("发布时间"), item.get("note_id", "")) or datetime.min.replace(tzinfo=TZ), reverse=True)
    return rows


def write_outputs(rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    final_rows = [{field: normalize_text(row.get(field, "")) for field in FIELDS} for row in rows]
    OUT_JSON.write_text(json.dumps({"meta": meta, "rows": final_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 小红书 InsForge 所有爬取帖子总表（精简列，正文评论补全）", ""]
    lines.append("| " + " | ".join(FIELDS) + " |")
    lines.append("| " + " | ".join(["---"] * len(FIELDS)) + " |")
    for row in final_rows:
        cells = []
        for field in FIELDS:
            if field == "帖子链接" and row.get(field):
                cells.append(f"[打开]({row[field]})")
            else:
                cells.append(markdown_escape(row.get(field, "")))
        lines.append("| " + " | ".join(cells) + " |")
    markdown = "\n".join(lines) + "\n"
    OUT_MD.write_text(markdown, encoding="utf-8")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(markdown, encoding="utf-8")

    FIELDS_JSON.write_text(
        json.dumps([{"name": field, "type": "text"} for field in FIELDS], ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    RECORDS_JSON.write_text(
        json.dumps({"fields": FIELDS, "rows": [[row.get(field, "") for field in FIELDS] for row in final_rows]}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    CURRENT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (CURRENT_OUTPUTS / OUT_JSON.name).write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    (CURRENT_OUTPUTS / OUT_MD.name).write_text(OUT_MD.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch missing bodies from Xiaohongshu detail pages.")
    parser.add_argument("--live-limit", type=int, default=None, help="Maximum number of missing-body rows to fetch in this run.")
    parser.add_argument("--sleep-min", type=float, default=2.5)
    parser.add_argument("--sleep-max", type=float, default=5.0)
    parser.add_argument("--page-wait-min", type=int, default=3800)
    parser.add_argument("--page-wait-max", type=int, default=6200)
    parser.add_argument("--cooldown-every", type=int, default=12)
    parser.add_argument("--cooldown-min", type=float, default=16.0)
    parser.add_argument("--cooldown-max", type=float, default=26.0)
    args = parser.parse_args()

    rows = load_rows()
    before_body_missing = sum(1 for row in rows if not normalize_text(row.get("帖子正文")))
    before_comment_missing = sum(1 for row in rows if not normalize_text(row.get("评论例子")))

    live_filled = 0
    live_empty_or_error = 0
    verify_required = False
    if args.live and before_body_missing:
        live_filled, live_empty_or_error, verify_required = fetch_live_bodies(
            rows,
            limit=args.live_limit,
            sleep_min=args.sleep_min,
            sleep_max=args.sleep_max,
            page_wait_min=args.page_wait_min,
            page_wait_max=args.page_wait_max,
            cooldown_every=args.cooldown_every,
            cooldown_min=args.cooldown_min,
            cooldown_max=args.cooldown_max,
        )

    for index, row in enumerate(rows, start=1):
        row["评论"] = ""
        row["评论例子"] = make_comment(row, index)

    body_missing = sum(1 for row in rows if not normalize_text(row.get("帖子正文")))
    comment_missing = sum(1 for row in rows if not normalize_text(row.get("评论例子")))
    comment_ai_flavor_hits = sum(1 for row in rows if any(pattern.search(row.get("评论例子", "")) for pattern in AI_FLAVOR_PATTERNS))
    meta = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source_json": str(SOURCE_JSON),
        "fields": FIELDS,
        "row_count": len(rows),
        "columns_removed_after_匹配关键词": ["来源类型", "来源文件", "来源数量", "note_id", "帖主昵称", "帖主主页链接", "点赞数", "收藏数", "评论数"],
        "before_body_missing": before_body_missing,
        "before_comment_missing": before_comment_missing,
        "live_enabled": args.live,
        "live_limit": args.live_limit,
        "live_filled": live_filled,
        "live_empty_or_error": live_empty_or_error,
        "verify_required": verify_required,
        "body_missing": body_missing,
        "comment_missing": comment_missing,
        "comment_ai_flavor_hits": comment_ai_flavor_hits,
        "cache_json": str(CACHE_JSON),
        "outputs": {
            "json": str(OUT_JSON),
            "markdown": str(OUT_MD),
            "inbox_markdown": str(INBOX_MD),
            "lark_fields": str(FIELDS_JSON),
            "lark_records": str(RECORDS_JSON),
        },
    }
    write_outputs(rows, meta)
    print(json.dumps({"status": "verify_required" if verify_required else "complete", **meta}, ensure_ascii=False, indent=2), flush=True)
    return 20 if verify_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
