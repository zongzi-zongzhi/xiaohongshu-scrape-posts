# Security Policy

## Supported Versions

当前项目以本地自动化脚本为主，未发布稳定版本。安全修复优先针对当前主分支和每日自动化主入口。

## Reporting a Vulnerability

如果发现以下问题，请不要公开提交真实密钥或敏感样例：

- API Key、Cookie、Token、账号密码泄露。
- 飞书 Base、表格或视图权限配置不当。
- 抓取结果包含不应公开的真实用户数据。
- 日志、截图、payload 或浏览器 profile 被误提交。

请通过私下渠道联系项目维护者，并提供复现步骤、影响范围和建议修复方式。

## Secret Handling

- `.env`、Cookie、Token、浏览器 profile、飞书 payload、抓取输出和日志均不得提交。
- `.env.example` 只能包含变量名和占位符。
- 飞书授权通过本机 `lark-cli.cmd` 登录态完成，不应把登录态写入仓库。
