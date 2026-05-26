# Agent Instructions

## Subagent Usage

When delegating tasks to subagents via the `Agent` tool:

- **Always prefer `run_in_background=true`** when launching subagents, unless the parent agent genuinely requires the result immediately before it can perform any other work.
- While subagents are running in the background, the parent agent should **continue with other work** (e.g., reading files, preparing edits, investigating unrelated parts of the codebase) rather than idly waiting.
- Only block and wait for subagent results when the next step is strictly dependent on their output.

This maximizes parallelism and keeps the session efficient.

## Development Rules

- **Never commit `venv/`** — The virtual environment is local-only and already excluded in `.gitignore`.
- **Run tests** with `python -m pytest tests/ -v` before committing test-related changes.
- **Bump `manifest.json` version** on every release to force Home Assistant cache invalidation.
- **Delete `__pycache__`** in `custom_components/nature_remo/` after major refactors before restarting HA, to avoid stale bytecode errors.
