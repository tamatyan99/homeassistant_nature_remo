# Agent Instructions

## Subagent Usage

- **Use subagents aggressively.** Delegate parallelizable work to child agents via the `Agent` tool and keep advancing unrelated tasks in the parent agent.
- Only block waiting for a child agent when its output is strictly required for the next step.
- **Prompt child agents for minimal output.** In the `prompt`, explicitly instruct the subagent to skip greetings, explanations, and status updates. It should perform the work and return only the final result (e.g., code, findings, or data) needed by the parent agent.
- **Write subagent prompts in English.** Even if the parent-agent conversation is in Japanese, issue the subagent's `prompt` in English to reduce token usage and improve model compliance.

## Development Rules

- **Never commit `venv/`** — The virtual environment is local-only and already excluded in `.gitignore`.
- **Run tests** with `python -m pytest tests/ -v` before committing test-related changes.
- **Bump `manifest.json` version** on every release to force Home Assistant cache invalidation.
- **Delete `__pycache__`** in `custom_components/nature_remo/` after major refactors before restarting HA, to avoid stale bytecode errors.
