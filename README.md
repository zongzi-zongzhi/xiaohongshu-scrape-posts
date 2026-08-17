# Xiaohongshu Scrape Posts

小红书 InsForge 建联线索池自动化程序。

这个仓库只保存程序源码和运行说明，不保存抓取结果、浏览器登录状态、飞书 payload、日志、截图、`.env` 或其他敏感文件。

## 功能

- 按规则文档读取目标用户、帖子特征、关键词库和输出字段。
- 抓取小红书新增候选帖子。
- 过滤招聘、课程、工具介绍、热榜、教程号等低质量内容。
- 根据飞书总表里“状态=不需要回”的记录生成负反馈画像。
- 输出本地 7 天滚动表。
- 通过 `lark-cli` 追加新增记录到固定飞书多维表格。

## 运行前准备

1. 安装 Python 依赖。
2. 安装 Playwright 浏览器。
3. 安装并登录 `lark-cli`。
4. 准备小红书浏览器 profile。
5. 准备规则文档。

默认规则文档路径：

```text
D:\czj note\小红书 InsForge 建联线索池规则总结.md
```

也可以用环境变量覆盖：

```powershell
$env:INSFORGE_XHS_RULE_DOC="D:\path\to\xhs-rules.md"
```

## 飞书配置

飞书目标表不要写死在公开源码里。运行时优先读取环境变量：

```powershell
$env:XHS_LARK_BASE_DOMAIN="https://your-domain.feishu.cn"
$env:XHS_LARK_BASE_TOKEN="your_base_token"
$env:XHS_LARK_TABLE_ID="your_table_id"
```

如果没有设置环境变量，程序会尝试读取本地：

```text
outputs/xhs_insforge_master_pointer.json
```

该文件被 `.gitignore` 排除，不应提交到仓库。

## 常用脚本

核心脚本：

```text
work/crawl_xhs_incremental_20260727_20260728_merge_existing.py
work/xhs_lead_quality.py
work/xhs_no_reply_filter.py
work/xhs_rules_doc.py
work/append_xhs_rows_to_fixed_lark_master.py
```

检查登录：

```powershell
python .\work\check_xhs_crawler_profile_20260809.py
```

打开可见登录窗口：

```powershell
python .\work\open_xhs_new_profile_login.py --keep-open
```

追加飞书前 dry-run：

```powershell
python .\work\append_xhs_rows_to_fixed_lark_master.py --source-json .\outputs\your-output.json --dry-run
```

正式追加飞书：

```powershell
python .\work\append_xhs_rows_to_fixed_lark_master.py --source-json .\outputs\your-output.json
```

## 安全边界

- 不真实评论。
- 不点赞。
- 不收藏。
- 不私信。
- 不发布内容。
- 不提交 `.env`、cookies、浏览器 profile、API Key、密码、抓取结果、日志和截图。
