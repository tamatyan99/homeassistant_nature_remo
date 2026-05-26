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
- **GitHub tag workflow** (for HACS):
  1. Update `manifest.json` version, commit, and push to `main`.
  2. Create a new lightweight tag: `git tag vX.Y.Z`
  3. Push the tag: `git push origin vX.Y.Z`
  4. If a tag already exists and must be moved, delete it locally and remotely first:
     `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z && git tag vX.Y.Z && git push origin vX.Y.Z`
  5. Avoid force-pushing tags whenever possible to prevent breaking downstream HACS caches.
- **Delete `__pycache__`** in `custom_components/nature_remo/` after major refactors before restarting HA, to avoid stale bytecode errors.

## Cursor Cloud specific instructions

### Environment

- Python 3.12 is required (matches CI).
- The sole dev dependency is `pytest-homeassistant-custom-component`, which transitively pulls in Home Assistant core, pytest, pytest-asyncio, aiohttp, and all test harness utilities.
- A virtualenv at `/workspace/venv` is created by the update script. Activate it with `source /workspace/venv/bin/activate`.

### Running tests

```
source /workspace/venv/bin/activate
python -m pytest tests/ -v
```

All external API calls are mocked; no network access or secrets are needed for the test suite.

### Linting / type checking

No linter or type checker is configured in this project. CI runs only `pytest`, `hassfest` (HA manifest validation), and HACS validation.

### Building / running the integration

This is a Home Assistant custom component, not a standalone application. It is loaded by HA at runtime from `custom_components/nature_remo/`. There is no build step. To test the integration end-to-end with a live HA instance, you would need a Nature Remo API access token (not required for unit tests).
