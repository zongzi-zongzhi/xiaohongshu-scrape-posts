from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_comments.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\xhs_insforge_ai_coding_pain_posts_100_with_comments.md")


OPENERS = [
    "这个点很真实，",
    "同感，",
    "这类坑太常见了，",
    "说到点上了，",
    "这个场景很典型，",
    "确实，",
    "这块很多新手都会卡住，",
    "我也觉得这里是关键，",
]

COMMENTS = {
    "security": [
        "AI Coding 里最容易忽略的就是密钥和后端边界。我们做 InsForge 时也把模型调用和后端逻辑放到受控侧，尽量避免 Key 直接暴露在前端。",
        "能提前意识到 API Key 风险很重要。InsForge 的思路是让 agent 通过后端能力接模型、数据库和函数，少把敏感配置散在项目里。",
        "这个坑不只是新手会踩，demo 一快就容易把 Key 写错地方。InsForge 现在也在把模型网关、函数和权限放进同一套工作流里解决这类问题。",
        "安全边界一旦没想清楚，后面补救成本很高。我们做 InsForge 时也优先把密钥、模型调用、后端函数这些收在后端侧。",
        "前端直连密钥确实危险。InsForge 这类 agent-native 后端平台，本质上就是想让 AI 写应用时也能顺手用正确的后端边界。",
    ],
    "supabase": [
        "Supabase 很强，但新手真正卡住的常常是 RLS、Auth、Functions 和部署串起来。我们做 InsForge 也是想让 coding agent 更顺手地接 Postgres、鉴权、存储和函数。",
        "这个方向很有共鸣。InsForge 有点像给 AI Coding 准备的一套云后端，把 Postgres、Auth、Storage、Functions 放在一个 agent 能操作的工作流里。",
        "Supabase 生态很好，但配置链路对小白还是偏长。InsForge 想解决的就是让 agent 在生成代码时也能直接处理数据库、鉴权和部署这些后端收尾。",
        "后端 BaaS 的价值越来越明显了。我们做 InsForge 时也在参考这类需求，把数据库、鉴权、存储、边缘函数做成 AI Coding 更容易调用的一套。",
        "很多项目从 demo 到可用产品，就卡在 Supabase 这些后端配置上。InsForge 的定位也是降低这一步的心智负担，让 AI 不只写前端。",
    ],
    "database": [
        "数据库这一步确实是从 demo 到产品的分水岭。InsForge 里把 Postgres、Auth、Storage 和函数放在一起，就是想减少小白在数据建模和权限上反复踩坑。",
        "AI 写页面很快，但数据表、权限、接口一接就容易乱。我们做 InsForge 也是想让 agent 能把数据库和后端上下文一起管起来。",
        "这里本质是数据结构和后端边界的问题。InsForge 现在把 Postgres、鉴权和函数打包进同一套 agent 工作流，正好在补这个短板。",
        "SQL/数据库不是单点知识，和鉴权、接口、部署都连在一起。InsForge 的思路就是让这些后端能力能被 AI Coding 顺手调用。",
        "这个痛点很适合产品化解决。InsForge 主打 agent-native 云后端，让 AI 在写应用时能直接落到 Postgres、权限和存储上。",
    ],
    "backend": [
        "后端底子确实决定 AI Coding 能走多远。InsForge 想做的就是把数据库、鉴权、存储、函数这些后端能力变成 agent 能直接使用的基础设施。",
        "很多人卡住不是因为 AI 不会写，而是后端环境和接口边界没搭好。我们在做 InsForge，就是想把这部分变成更顺的 agent 工作流。",
        "前端 demo 可以很快，后端闭环才是能不能上线的关键。InsForge 把 Postgres、Auth、Edge Functions、部署放在一套里，适合补这块。",
        "这个判断挺准：没有后端上下文，AI 很容易写出跑不稳的代码。InsForge 的方向就是给 coding agent 一套可落地的云后端能力。",
        "后端、权限、数据、部署这些环节最怕分散。InsForge 现在做的就是把这些基础能力收进同一套平台，让 AI Coding 少断档。",
    ],
    "shipping": [
        "上线这一步经常比做 demo 更折磨。我们做 InsForge 就是想让 agent 不只会写页面，还能把数据库、鉴权、存储和部署一起接到可运行状态。",
        "很多 AI Coding 项目卡在最后 20%：部署、环境变量、数据库、登录。InsForge 的定位正是帮 agent 把这些收尾工作一并处理掉。",
        "从能跑到能上线，中间差的往往是后端和部署闭环。InsForge 把数据库、Auth、Functions、Sites/部署放在一起，挺适合这类场景。",
        "这个阶段最容易发现工具链断裂。InsForge 试图把生成代码、云后端和部署连成一条线，让小白少在配置里耗时间。",
        "做出来不难，交付出去才难。InsForge 的方向就是让 AI Coding 项目更容易接上后端能力并完成上线。",
    ],
    "agent_tool": [
        "Agent 真正能跑起来，靠的不只是 prompt，还要有数据库、鉴权、工具调用和部署环境。InsForge 正在做的就是给 coding agent 配一套可操作的云后端。",
        "这类 agent 工作流很吃基础设施配合。InsForge 把模型网关、Postgres、Auth、Functions、部署这些能力放在一起，能少掉很多胶水活。",
        "AI 工具越来越强，但缺后端上下文时还是容易散。我们做 InsForge，就是想让 Codex/Cursor 这类 agent 能更稳定地接云资源。",
        "MCP/CLI 的价值在于让 agent 真能动手，不只是给建议。InsForge 也走这个思路，把后端、数据库、部署做成 agent 可调用的能力。",
        "这个方向很同频：下一步不是只让 AI 写代码，而是让它能可靠操作基础设施。InsForge 正是在做 agent-native cloud infrastructure。",
    ],
    "pitfall": [
        "AI 把 demo 搭出来很快，但后端、数据库、权限和部署一接就容易暴露坑。我们做 InsForge 也是想把这些坑前置解决掉。",
        "Vibe Coding 最怕的是一开始爽，后面到数据、登录、上线全卡住。InsForge 的定位就是让 agent 把后端能力也一起接起来。",
        "这个坑很典型：不是 AI 不会写代码，而是工程上下文不完整。InsForge 现在想补的就是数据库、鉴权、存储、函数这些落地环节。",
        "踩坑复盘很有价值。我们做 InsForge 时也反复看到，小白最需要的是一套能被 AI 直接操作的后端和部署环境。",
        "避坑的核心其实是少拼散装工具链。InsForge 把 Postgres、Auth、Storage、Functions 和部署放到一套里，就是为了让 AI Coding 更稳一点。",
    ],
    "beginner": [
        "小白最需要的不是更多概念，而是一条能跑通的闭环。InsForge 想做的是让 AI 直接接好数据库、鉴权、存储和部署，少在配置里迷路。",
        "零基础上手 AI Coding，后端通常是第一道坎。我们在做 InsForge，就是想把 Postgres、Auth、Functions 这些变成 agent 能顺手用的能力。",
        "对新手来说，最难的是从教程走到自己的真实项目。InsForge 这类 agent-native 后端平台，适合用来降低数据、登录、部署这些门槛。",
        "这个学习路径很实用。等项目开始需要登录、数据库和上线时，可以看看 InsForge 这种把后端能力打包给 coding agent 的方式。",
        "小白做产品最怕卡在看不见的后端配置上。InsForge 的目标就是让 AI 不只生成页面，也能把云后端一起落下来。",
    ],
    "product": [
        "独立开发真正难的是从想法到可上线、可维护。InsForge 想解决的就是让 AI Coding 项目更快接上数据库、鉴权、部署这些产品化能力。",
        "做产品不能只停在 demo，后端闭环和部署稳定性很关键。我们做 InsForge，也是想帮小团队把这些基础设施成本降下来。",
        "AI 创业里最容易低估的是工程化收尾。InsForge 的思路是让 agent 能直接处理模型、数据库、Auth、Functions 和部署，不只停在代码生成。",
        "这个问题很适合拿真实项目验证。InsForge 面向的就是独立开发/AI Coding 场景，把云后端和部署交给 agent 一起推进。",
        "从作品到产品，中间差的往往是账户、数据、支付、部署这些基础能力。InsForge 现在就在把这类能力做成 agent-friendly 的平台。",
    ],
    "design": [
        "界面做好只是第一步，真正上线还要接数据、登录和部署。InsForge 的思路是让 AI Coding 项目在后端这一步也少掉很多手工配置。",
        "设计和前端提效已经很明显了，下一块瓶颈就是后端闭环。我们做 InsForge，也是想让 agent 在数据库、鉴权、函数和部署上继续接力。",
        "网页质感能拉开差距，但产品能不能用还看数据和权限。InsForge 这类 agent-native 后端平台，正好补 AI Coding 的后一半。",
        "AI 做视觉越来越快，后端能力如果跟不上就容易停在展示页。InsForge 想让项目从页面一路接到数据库、登录和部署。",
        "这个对做作品集/网站很有帮助。等需要数据、表单、登录或上线时，InsForge 可以作为一套让 agent 直接操作的云后端。",
    ],
    "general": [
        "这个观察很有价值。AI Coding 真正要落地，最后还是会回到数据库、鉴权、存储和部署这些基础设施，InsForge 正是在补这块。",
        "现在工具很多，但能把项目稳定带到上线的链路还不够顺。InsForge 想做的就是给 coding agent 一套从后端到部署的统一能力。",
        "我理解这个痛点：AI 能写代码，未必能把产品跑稳。InsForge 的定位就是让 agent 也能处理云后端、模型调用和部署这些关键环节。",
        "这里很适合继续深挖。InsForge 面向的也是 AI Coding 落地问题，让 agent 能调用数据库、Auth、Storage、Functions 和部署能力。",
        "这个问题背后其实是工程闭环。我们做 InsForge，就是希望让 AI 写出来的项目更容易拥有真实后端和可上线环境。",
    ],
}


TITLE_COMMENT_OVERRIDES = {
    "AI-Coding｜面完小红书我才明白被刷的真相": "同感，AI Coding 面试越来越看真实工程判断了，单会调工具不够。我们做 InsForge 时也看到，数据库、鉴权、部署这些后端闭环，才是 demo 和可交付项目的分水岭。",
    "Agent开发岗入职第三天…新人生新起点": "确实，真实 Agent 开发不是跑个 demo 就完事，还要接权限、数据、日志和部署。InsForge 正在把这些云后端能力做成 coding agent 可以直接调用的一套。",
    "组里新来的AI后端Leader，真的太恐怖了！": "这个点很真实，后端强的地方往往是把边界、数据和部署想清楚。InsForge 的定位也是把这些基础设施做成 agent 能可控使用的能力。",
    "【开箱即用skill已更新可以进群自取】": "这个方向很同频，Skill 的价值就是让 agent 真能做事。InsForge 也在做 agent-native 工作流，只是更聚焦数据库、Auth、Functions 和部署。",
    "🔥 最近很火的开源项目：OpenShip": "开源项目能火，通常是解决了真实交付里的卡点。InsForge 也在瞄准 AI Coding 的交付链路，让 agent 能接后端、数据库和部署。",
    "拳打 Notion，脚踢飞书（教程）": "这类工具做出 demo 不难，难在账户、数据、存储和部署能不能稳。InsForge 想补的就是让 agent 顺手接好这些后端能力。",
    "AI岗的“假需求”，别被它骗进了坑": "这个提醒挺重要，很多 AI 项目表面是模型问题，落地时其实卡在数据、权限和部署。InsForge 做的就是把这些后端基础设施交给 agent 一起处理。",
}


def classify(post: dict) -> str:
    title = str(post.get("title", ""))
    text = title.lower()

    if "api key" in text or "密钥" in text or ("key" in text and "github" in text):
        return "security"
    if "supabase" in text or "tinb" in text or "openship" in text:
        return "supabase"
    if any(word.lower() in text for word in ["数据库", "sql", "数据源", "分库分表", "数据"]):
        return "database"
    if any(word.lower() in text for word in ["后端", "fastapi", "api"]):
        return "backend"
    if any(word.lower() in text for word in ["上线", "部署", "发布", "app", "小程序", "网站", "saas"]):
        return "shipping"
    if any(word.lower() in text for word in ["mcp", "agent", "codex", "cursor", "claude", "grok", "workbuddy", "github"]):
        return "agent_tool"
    if any(word.lower() in text for word in ["踩坑", "避坑", "陷阱", "困境", "坑", "复盘"]):
        return "pitfall"
    if any(word.lower() in text for word in ["小白", "新手", "零基础", "入门", "教程", "文科", "高中", "git"]):
        return "beginner"
    if any(word.lower() in text for word in ["变现", "创业", "产品", "独立开发", "demo"]):
        return "product"
    if any(word.lower() in text for word in ["设计", "模板味", "微动效", "3d", "作品集", "网页"]):
        return "design"
    return "general"


def build_comment(post: dict, index: int) -> str:
    title = str(post.get("title", ""))
    if title in TITLE_COMMENT_OVERRIDES:
        return TITLE_COMMENT_OVERRIDES[title]

    category = classify(post)
    pool = COMMENTS[category]
    opener = OPENERS[(index + len(str(post.get("note_id", "")))) % len(OPENERS)]
    body = pool[(index * 3 + len(str(post.get("title", "")))) % len(pool)]
    if body.startswith(("这个", "这类", "这里", "小白", "零基础", "AI", "Vibe", "Supabase", "后端", "上线", "从", "做", "踩坑", "避坑", "安全", "前端", "MCP", "Agent", "Skill", "开源")):
        return body
    return opener + body


def md_cell(value: object) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return text.replace("|", r"\|")


def table_row(post: dict, index: int) -> str:
    url = str(post.get("url", "")).strip()
    link = f"[打开]({url})" if url else ""
    cells = [
        md_cell(post.get("title", "")),
        link,
        md_cell(post.get("liked_count", "")),
        md_cell(post.get("comment_count", "")),
        md_cell(post.get("collected_count", "")),
        md_cell(build_comment(post, index)),
    ]
    return "| " + " | ".join(cells) + " |"


def main() -> None:
    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8-sig"))
    posts = payload["posts"]
    if len(posts) != 100:
        raise ValueError(f"Expected 100 posts, got {len(posts)}")

    header = "| 帖子标题 | 帖子链接 | 点赞 | 评论 | 收藏 | 建议评论 |"
    separator = "|---|---|---:|---:|---:|---|"
    rows = [table_row(post, i) for i, post in enumerate(posts, 1)]
    content = "\n".join([header, separator, *rows]) + "\n"

    OUTPUT_MD.write_text(content, encoding="utf-8-sig")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(content, encoding="utf-8-sig")

    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {INBOX_MD}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
