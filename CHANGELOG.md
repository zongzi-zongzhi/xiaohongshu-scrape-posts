# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Added PRD, technical architecture, project structure, development log, and roadmap documents.
- Added environment variable example for local configuration.
- Added GitHub issue templates, pull request template, and basic CI workflow.
- Added minimal unit test for CSDN rule document loading.
- Added importable `src/insforge_social_lead/csdn/` package modules for the maintained CSDN pipeline.
- Added CSDN compatibility wrappers under `work/` so the existing automation command keeps working.
- Added protocol-required placeholder directories for crawler, analyzer, prompts, UI, utilities, scripts, examples, and assets.

### Changed

- Updated README from a Xiaohongshu-only note to the current InsForge social lead crawler overview.
- Changed CSDN rule document path to support `CSDN_RULE_DOC_PATH` while keeping the existing default path.
- Updated `.gitignore` so maintained CSDN source scripts are visible to Git while generated outputs remain ignored.
- Moved maintained CSDN implementation from ignored `work/` scripts into the importable `src/` package.
- Changed CSDN Feishu target loading to happen only when Feishu operations run, not during module import.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Fixed the project visibility issue where CSDN core scripts were ignored by Git.

### Security

- Documented secret, cookie, token, browser profile, and local output handling.
