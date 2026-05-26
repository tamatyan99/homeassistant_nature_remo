# Agent Instructions

## Subagent Usage

- **積極的にサブエージェントを使うこと。** 並列処理できる作業は積極的に `Agent` ツールで子エージェントに任せ、親エージェントは別の作業を進める。
- 子エージェントの結果が次のステップに必須な場合のみ、その完了を待つ。

## Development Rules

- **Never commit `venv/`** — The virtual environment is local-only and already excluded in `.gitignore`.
- **Run tests** with `python -m pytest tests/ -v` before committing test-related changes.
- **Bump `manifest.json` version** on every release to force Home Assistant cache invalidation.
- **Delete `__pycache__`** in `custom_components/nature_remo/` after major refactors before restarting HA, to avoid stale bytecode errors.
