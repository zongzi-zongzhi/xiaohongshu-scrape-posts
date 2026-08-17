import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\Administrator\Documents\Codex\2026-07-22\insforge-superbass")
SKILL_DIR = Path(r"C:\Users\Administrator\.codex\skills\xiaohongshu-skill")
OUTPUT_DIR = ROOT / "outputs"
RAW_DIR = ROOT / "work" / "xhs_raw"

KEYWORDS = [
    "Supabase 坑",
    "Supabase 劝退",
    "Supabase 翻车",
    "Supabase 后端",
    "Supabase 数据库",
    "Supabase RLS",
    "Supabase 安全",
    "Supabase 部署",
    "Supabase 替代",
    "Firebase 替代",
    "后端开发 痛点",
    "后端 崩溃",
    "后端 开发 坑",
    "后端 太难了",
    "后端 现状",
    "前端 操作数据库 安全",
    "前端 后端 数据库",
    "数据库 崩溃",
    "数据库 连接 问题",
    "数据库 设计 坑",
    "数据库 新手",
    "数据库 部署",
    "独立开发 后端",
    "独立开发 数据库",
    "独立开发 技术栈",
    "独立开发 SaaS",
    "独立开发 踩坑",
    "程序员 独立开发 坑",
    "AI 编程 后端",
    "AI coding 后端",
    "vibe coding 坑",
    "Cursor 后端 数据库",
    "MCP 后端",
    "API 密钥 泄露",
    "全栈 项目 技术选型",
    "自建后端 坑",
    "服务器 部署 坑",
]

PAIN_PATTERNS = [
    ("Supabase/RLS/安全", ["supabase", "rls", "安全", "前端操作数据库", "密钥", "泄露"]),
    ("后端搭建/部署", ["后端", "部署", "服务器", "云服务", "接口", "api"]),
    ("数据库设计/连接", ["数据库", "postgres", "连接", "表结构", "schema", "sql"]),
    ("独立开发成本/选型", ["独立开发", "saas", "技术栈", "穷鬼", "成本", "选型"]),
    ("AI Coding 后端闭环", ["ai", "agent", "cursor", "vibe", "mcp", "coding"]),
]

INTENT_WORDS = [
    "坑",
    "劝退",
    "翻车",
    "崩溃",
    "危险",
    "安全",
    "泄露",
    "痛点",
    "现状",
    "太难",
    "问题",
    "新手",
    "注意",
    "成本",
    "穷鬼",
    "选型",
    "怎么选",
    "替代",
    "不要",
    "必看",
]


def extract_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON object found in command output")


def to_int(value) -> int:
    if value is None:
        return 0
    s = str(value).strip().lower().replace(",", "")
    if not s:
        return 0
    multiplier = 1
    if s.endswith("w") or s.endswith("万"):
        multiplier = 10000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except ValueError:
        digits = re.sub(r"\D", "", s)
        return int(digits) if digits else 0


def classify(title: str, keyword: str) -> tuple[str, str, int]:
    haystack = f"{title} {keyword}".lower()
    categories = []
    for category, words in PAIN_PATTERNS:
        if any(word.lower() in haystack for word in words):
            categories.append(category)
    if not categories:
        categories.append("泛开发痛点")

    score = 0
    for word in INTENT_WORDS:
        if word.lower() in haystack:
            score += 3
    for word in ["supabase", "后端", "数据库", "独立开发", "ai", "agent", "cursor", "vibe"]:
        if word in haystack:
            score += 2
    return "、".join(categories), ",".join([w for w in INTENT_WORDS if w.lower() in haystack]), score


def outreach_angle(category: str, title: str) -> str:
    text = title.lower()
    if "Supabase" in category or "supabase" in text or "rls" in text:
        return "可从 Supabase 使用门槛、安全/RLS、替代方案切入，介绍 InsForge 的 Postgres/Auth/Storage/Functions 一体化和 agent-native 工作流。"
    if "AI Coding" in category:
        return "可从 AI 编程无法真正完成后端闭环切入，介绍 InsForge 让 coding agent 直接操作数据库、Auth、部署和模型网关。"
    if "独立开发" in category:
        return "可从独立开发者降成本、少拼接服务、快速上线 MVP 切入，强调 InsForge 一套基础设施覆盖常见 SaaS 后端需求。"
    if "数据库" in category:
        return "可从数据库建模、连接、权限、上线维护的麻烦切入，介绍 InsForge 的托管 Postgres 与配套后端能力。"
    return "可从后端搭建和部署耗时切入，介绍 InsForge 帮小团队减少基础设施配置。"


def run_search(keyword: str, limit: int = 20) -> dict:
    cmd = [
        "python",
        "-m",
        "scripts",
        "search",
        keyword,
        "--limit",
        str(limit),
        "--headless",
        "true",
    ]
    proc = subprocess.run(
        cmd,
        cwd=SKILL_DIR,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=150,
    )
    raw = proc.stdout
    (RAW_DIR / f"search_{safe_name(keyword)}.log").write_text(raw, encoding="utf-8")
    data = extract_json(raw)
    data["_returncode"] = proc.returncode
    return data


def safe_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value).strip("_")


def make_url(note_id: str, xsec_token: str) -> str:
    return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    seen = {}
    failures = []
    for index, keyword in enumerate(KEYWORDS, start=1):
        print(f"[{index}/{len(KEYWORDS)}] searching: {keyword}", flush=True)
        try:
            data = run_search(keyword)
        except Exception as exc:
            failures.append({"keyword": keyword, "error": str(exc)})
            time.sleep(8)
            continue

        for item in data.get("results", []):
            note_id = str(item.get("id") or "").strip()
            title = str(item.get("title") or "").strip()
            user = str(item.get("user") or "").strip()
            token = str(item.get("xsec_token") or "").strip()
            if not note_id or not title or not user or "#" in note_id:
                continue
            record = seen.get(note_id)
            if record is None:
                category, intent_words, score = classify(title, keyword)
                record = {
                    "note_id": note_id,
                    "xsec_token": token,
                    "url": make_url(note_id, token),
                    "title": title,
                    "type": item.get("type", ""),
                    "author": user,
                    "author_id": item.get("user_id", ""),
                    "liked_count": to_int(item.get("liked_count")),
                    "collected_count": to_int(item.get("collected_count")),
                    "comment_count": to_int(item.get("comment_count")),
                    "shared_count": to_int(item.get("shared_count")),
                    "matched_keywords": [keyword],
                    "pain_category": category,
                    "pain_signal_words": intent_words,
                    "pain_score": score,
                    "outreach_angle": outreach_angle(category, title),
                    "cover_url": item.get("cover_url", ""),
                }
                seen[note_id] = record
            else:
                record["matched_keywords"].append(keyword)
                category, intent_words, score = classify(record["title"], " ".join(record["matched_keywords"]))
                record["pain_category"] = category
                record["pain_signal_words"] = intent_words
                record["pain_score"] = max(record["pain_score"], score)

        time.sleep(5 if index % 4 else 12)

    records = list(seen.values())
    for record in records:
        engagement = record["liked_count"] + record["collected_count"] + record["comment_count"] * 2 + record["shared_count"] * 2
        record["engagement_score"] = engagement
        record["matched_keywords"] = "、".join(dict.fromkeys(record["matched_keywords"]))

    records.sort(
        key=lambda r: (
            r["pain_score"],
            r["comment_count"],
            r["engagement_score"],
            r["collected_count"],
        ),
        reverse=True,
    )
    selected = records[:100]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = {
        "generated_at": timestamp,
        "source": "xiaohongshu-skill python -m scripts search",
        "keywords": KEYWORDS,
        "unique_candidates": len(records),
        "selected_count": len(selected),
        "failures": failures,
    }

    json_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100.json"
    csv_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100.csv"
    md_path = OUTPUT_DIR / "xhs_insforge_pain_posts_100.md"

    json_path.write_text(
        json.dumps({"meta": meta, "posts": selected}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "note_id",
        "url",
        "title",
        "type",
        "author",
        "author_id",
        "liked_count",
        "collected_count",
        "comment_count",
        "shared_count",
        "engagement_score",
        "matched_keywords",
        "pain_category",
        "pain_signal_words",
        "outreach_angle",
        "cover_url",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in selected:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    lines = [
        "# 小红书 InsForge 建联痛点帖子 100 条",
        "",
        f"- 生成时间：{timestamp}",
        f"- 候选去重后：{len(records)} 条",
        f"- 本次选取：{len(selected)} 条",
        "- 数据来源：本地小红书 skill 搜索公开结果；未执行评论、点赞、收藏、私信、发布。",
        "",
        "| # | 标题 | 作者 | 互动 | 痛点分类 | 触达角度 | 链接 |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for idx, row in enumerate(selected, start=1):
        title = row["title"].replace("|", "\\|")
        author = row["author"].replace("|", "\\|")
        category = row["pain_category"].replace("|", "\\|")
        angle = row["outreach_angle"].replace("|", "\\|")
        lines.append(
            f"| {idx} | {title} | {author} | {row['engagement_score']} | {category} | {angle} | [打开]({row['url']}) |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(str(csv_path))
    print(str(md_path))


if __name__ == "__main__":
    main()
