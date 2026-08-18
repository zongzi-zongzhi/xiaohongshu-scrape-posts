# Contributing

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Validation

提交改动前至少运行：

```powershell
python -m unittest discover -s tests
python -m py_compile work\csdn_feedback_quality_rules.py work\csdn_daily_incremental_to_master_and_lark.py
```

涉及飞书写入的改动，应优先使用 `--no-lark` 做本地 dry-run。

## Documentation

如果改动影响需求、架构、文件结构、运行方式或安全边界，需要同步更新：

- `README.md`
- `docs/PRD.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/DEV_LOG.md`
- `CHANGELOG.md`

## Commit Message

建议使用约定式提交：

```text
feat(csdn): add rule document loader
fix(lark): preserve custom fields during upsert
docs: update CSDN automation architecture
test(csdn): add rule document loading test
```
