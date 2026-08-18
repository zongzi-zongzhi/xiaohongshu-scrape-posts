# Xiaohongshu Scrape Posts

Local Xiaohongshu lead crawler for InsForge. It helps find recent Xiaohongshu posts from people who are already building apps, websites, SaaS, MVPs, mini programs, or independent products with AI coding tools, but are blocked by backend, database, auth, permission, API key, Vercel deployment, environment variables, or data persistence.

The project is designed for a daily local automation. It only crawls and organizes candidate posts, then appends new rows to one fixed Feishu Base table. It must not comment, like, collect, follow, message, publish, or change Feishu permissions.

## Current Rule Source

The automation reads a human-editable Markdown rule document before each run:

```powershell
D:\czj note\小红书 InsForge 建联线索池规则总结.md
```

You can override it with:

```powershell
$env:INSFORGE_XHS_RULE_DOC="D:\path\to\rules.md"
```

The rule document controls target user profile, target post features, keywords, disabled topics, output fields, daily quantity limits, and negative feedback learning behavior.

## Target Posts

Core selection rule:

> The post should look like it was written by a person who is building a real project and is blocked by backend, database, login/auth, permission, API key, deployment, environment variables, or data saving. It can also be written by someone who can build projects but clearly complains that manually configuring backend capabilities is too troublesome. Do not collect content-farm posts that teach beginners to merely recognize AI coding tools.

Preferred signals:

- First-person builder language: "I built an app", "I used AI to make a site", "I am stuck".
- Real project context: app, website, SaaS, MVP, mini program, independent development.
- Backend pain: backend, database, Supabase, Auth, RLS, API Key, Vercel, deployment, environment variables, data saving.
- Help or failure wording: help, how to fix, stuck, failed, error, cannot configure.
- Configuration friction: manual setup is troublesome, repeated setup is annoying, does not want to configure backend manually.

Reject or down-rank:

- AI coding tool introductions.
- Cursor, Claude Code, Trae, Lovable, Bolt, WorkBuddy beginner tutorials without a project/backend problem.
- Study check-ins, Day N posts, note collections, tool lists.
- GitHub trending, project lists, daily news, pure information posts.
- Courses, bootcamps, private coaching, paid communities, material sales.
- Recruiting, internships, resumes, job seeking, interviews.
- Pure concept explainers, academic papers, design showcases, events.

## Output Fields

The current fixed local and Feishu output fields are exactly:

1. 发布时间
2. 帖子名字
3. 帖子链接
4. 评论
5. 匹配关键词
6. 备注

`评论` and `备注` stay empty for the user to fill manually. The automation no longer outputs post body, body excerpt, or comment examples.

## Feishu Master Table

The Feishu side uses one fixed Base table. The daily job appends only new Xiaohongshu links and never creates a new Base or table unless the user explicitly asks.

Do not hard-code private Feishu tokens in source code. Configure them through environment variables:

```powershell
$env:XHS_LARK_BASE_DOMAIN="https://your-domain.feishu.cn"
$env:XHS_LARK_BASE_TOKEN="your_base_token"
$env:XHS_LARK_TABLE_ID="your_table_id"
```

The local ignored pointer file can also provide runtime config:

```powershell
outputs\xhs_insforge_master_pointer.json
```

`outputs/` is ignored and must not be committed.

## Negative Feedback Learning

Before writing to Feishu, the automation reads the fixed master table and learns from rows whose `状态` value is `不需要回`.

Rules:

- Exact duplicate Xiaohongshu note IDs are skipped.
- Keywords with a high `不需要回` ratio are downweighted by 30%-60%.
- A keyword is paused if it appears with `不需要回` for 3 consecutive days and has no recent positive feedback.
- Tutorial, beginner, trending, list, daily news, and tool-collection patterns are pushed back or rejected unless there is a specific backend/deploy/database problem.

Positive status values such as `已回` or `已评论` are treated as signals to keep related topics alive.

## Daily CLI

Run from the project root:

```powershell
python .\scripts\xhs_cli.py health
python .\scripts\xhs_cli.py rules
python .\scripts\xhs_cli.py check-login
python .\scripts\xhs_cli.py open-login --keep-open
python .\scripts\xhs_cli.py crawl --fresh --max-keywords 35 --scroll-rounds 3
python .\scripts\xhs_cli.py append --source-json outputs\your_daily_output.json --dry-run
python .\scripts\xhs_cli.py append --source-json outputs\your_daily_output.json
```

Use `open-login` only when Xiaohongshu requires login, QR verification, safety verification, or cooldown. Do not keep refreshing QR codes when the platform says operations are too frequent.

## Daily Acceptance

- Health checks pass before crawling.
- Rule document is readable.
- Candidate posts match the InsForge backend/database/deployment pain profile.
- Daily Feishu append target is 25-50 new rows when enough qualified posts are available.
- Do not lower the quality bar or duplicate existing links just to reach the minimum.
- Local rolling output is saved under `outputs/`.
- Feishu append writes only new rows to the fixed master table.
- No real platform interaction is performed.

## Project Layout

```text
scripts/xhs_cli.py
src/xiaohongshu_scrape_posts/
  cli.py
  rules.py
  quality.py
  feedback.py
  paths.py
  crawler/legacy.py
  integrations/lark.py
work/
  append_xhs_rows_to_fixed_lark_master.py
  bound_connect_proxy.py
  check_xhs_crawler_profile_20260809.py
  crawl_xhs_incremental_20260727_20260728_merge_existing.py
  open_xhs_new_profile_login.py
  xhs_lead_quality.py
  xhs_no_reply_filter.py
  xhs_rules_doc.py
docs/
examples/
tests/
```

`work/` contains only compatibility wrappers and the baseline historical crawler required by the current daily flow. Runtime caches, payloads, screenshots, profiles, and generated outputs are ignored.

## Verification

```powershell
python -m unittest discover -s tests
python .\scripts\xhs_cli.py health
python .\scripts\xhs_cli.py rules
```

## Safety

- Do not commit `.env`, cookies, browser profiles, token files, Feishu payloads, screenshots, generated outputs, or raw scrape caches.
- Do not publish user-specific Feishu Base URLs or private tokens.
- Do not perform comments, likes, collections, follows, private messages, or posts.
