# PRD: Xiaohongshu Scrape Posts

## Problem

InsForge needs a repeatable way to find Chinese Xiaohongshu posts from builders who can create pages, demos, or product prototypes with AI coding tools but are blocked by backend work.

The valuable leads are not generic beginners learning AI tools. They are people with a concrete project and a backend, database, login, permission, API key, deployment, environment variable, or data-saving problem.

## Goal

Create a local daily automation that:

- reads the Markdown rule document before every run
- crawls recent Xiaohongshu posts from yesterday 00:00 to the run time, or a manually requested window
- filters candidates by the InsForge builder pain profile
- reads Feishu `状态=不需要回` rows as negative feedback
- appends only new links to one fixed Feishu Base table
- writes local rolling outputs for audit

## Non-Goals

- No real comments, likes, collections, follows, private messages, or posting.
- No Feishu Base or table creation during daily runs.
- No Feishu permission changes.
- No hard-coded Feishu tokens in public source code.
- No scraping of unrelated platforms in this repository.

## Output Fields

1. 发布时间
2. 帖子名字
3. 帖子链接
4. 评论
5. 匹配关键词
6. 备注

`评论` and `备注` must be empty strings when appended by automation.

## Quality Target

Daily write target: at least 25 and at most 50 new Feishu rows when enough qualified posts exist.

Quality has priority over count. The crawler must not add tutorials, tool lists, trending posts, recruiting, courses, or duplicates just to hit the minimum.

## User Feedback Loop

The user marks rows in Feishu using the `状态` column. `不需要回` means future crawling should reduce similar posts. `已回` or `已评论` means similar topics can remain active.
