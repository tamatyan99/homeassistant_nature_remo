# Agent Instructions

This file contains context and conventions for AI agents working on the Nature Remo Home Assistant custom integration.

---

## Project Overview

- **Name:** Nature Remo – Home Assistant Custom Integration
- **Repository:** `tamatyan99/homeassistant_nature_remo`
- **Domain:** `nature_remo`
- **Language:** Python 3.12
- **Type:** Home Assistant custom component (HACS-compatible)
- **Integration mode:** Hub, cloud polling with optional local API

The integration polls the Nature Remo Cloud API (`https://api.nature.global/1`) and exposes climate, light, sensor, remote, switch, binary_sensor, event, button, and select entities.

---

## Subagent Usage

- **Use subagents aggressively.** Delegate parallelizable work to child agents via the `Agent` tool and keep advancing unrelated tasks in the parent agent.
- Only block waiting for a child agent when its output is strictly required for the next step.
- **Prompt child agents for minimal output.** In the `prompt`, explicitly instruct the subagent to skip greetings, explanations, and status updates. It should perform the work and return only the final result (e.g., code, findings, or data) needed by the parent agent.
- **Write subagent prompts in English.** Even if the parent-agent conversation is in Japanese, issue the subagent's `prompt` in English to reduce token usage and improve model compliance.

---

## Development Environment

### Python Version

Python 3.12 is required. This matches CI and `pyproject.toml` (`requires-python = ">=3.12"`).

### Installing Dependencies

```bash
python3 -m pip install --upgrade pip
pip install -e .[dev]
```

This installs:
- `pytest>=8.0`
- `pytest-asyncio>=0.24`
- `pytest-homeassistant-custom-component>=0.13`
- `ruff>=0.6`
- `mypy>=1.11`

### Virtual Environment

A project-level virtualenv is recommended but not pre-configured. If you create one, name it `venv/` or `.venv/` — both are already ignored in `.gitignore`.

---

## Running Checks

### Tests

```bash
python3 -m pytest tests/ -v --tb=short
```

All external API calls are mocked; no network access or secrets are needed.

### Lint

```bash
python3 -m ruff check custom_components/nature_remo/ tests/
```

Auto-fix where safe:

```bash
python3 -m ruff check custom_components/nature_remo/ tests/ --fix
```

### Type Check

```bash
python3 -m mypy custom_components/nature_remo/
```

> **Note:** As of the current codebase, `mypy` reports pre-existing type errors (mostly HA generics and override signatures). These are informational and do not block CI (`continue-on-error: true` in `test.yml`). Fix them only when touching the relevant code.

---

## Project Structure

```
custom_components/nature_remo/
├── __init__.py          # Entry setup, platform forwarding, service handlers
├── api.py               # aiohttp wrapper for Nature Remo cloud + optional local API
├── binary_sensor.py     # Motion detection state
├── button.py            # Learn signal / refresh data buttons
├── climate.py           # Air conditioner entities
├── config_flow.py       # Initial setup / reauth flow
├── const.py             # Domain, constants, HVAC mode maps, smart-meter EPCs
├── coordinator.py       # DataUpdateCoordinator, device/appliance classification
├── diagnostics.py       # Redacted diagnostics dump
├── entity.py            # Shared DeviceInfo helper
├── event.py             # Motion detected event entity
├── light.py             # Light entities + service registration
├── manifest.json        # Integration metadata (version must be bumped on release)
├── options_flow.py      # Update interval, motion threshold, local IP, external sensors
├── remote.py            # Generic IR remote entities
├── select.py            # Light mode + AC preset selectors
├── sensor.py            # Temperature, humidity, illuminance, pressure, power, motion time
├── services.yaml        # Custom service definitions
├── strings.json         # Translation keys
├── switch.py            # On/off switch for IR remotes with power signals
└── translations/        # en.json, ja.json
```

---

## Architecture Patterns

- **Hub-style config flow** — one config entry per API key.
- **Single coordinator per entry** — all platforms read from one `NatureRemoCoordinator` stored at `hass.data[DOMAIN][entry.entry_id]`.
- **Cloud + optional local access** — `api.py` branches between cloud URL and `http://{local_ip}`. Local API is used only for IR message sending; data fetch always uses the cloud.
- **Rate-limit awareness** — response headers are logged; `429` responses trigger retry with `Retry-After` / `X-Rate-Limit-Reset` awareness. Cloud requests are serialized with `asyncio.Lock` to avoid bursts.
- **PII redaction** — `diagnostics.py` recursively masks sensitive keys (`id`, `name`, `nickname`, `device_id`, `appliance_id`, `serial_number`, `mac_address`).

---

## Coding Conventions

- Target Python 3.12.
- Follow existing ruff rules configured in `pyproject.toml` (`E`, `W`, `F`, `I`, `N`, `UP`, `B`, `C4`, `SIM`; `E501` ignored).
- Import order is enforced by ruff (`I`). First-party package: `custom_components.nature_remo`.
- Use `contextlib.suppress(...)` instead of bare `try/except/pass` where appropriate.
- In `except` clauses, use `raise ... from err` or `raise ... from None` (rule `B904`).
- Keep entity state updates optimistic and provide rollback on `ClientError` / `TimeoutError`.

---

## Testing Conventions

- Use `pytest-homeassistant-custom-component` fixtures and `MockConfigEntry`.
- Mock `NatureRemoAPI` methods or `api._session.request` — never call real endpoints in tests.
- The `auto_enable_custom_integrations` fixture in `tests/conftest.py` is autouse; custom components are loaded automatically.
- Add tests when modifying config/options flow or coordinator behavior.

---

## GitHub Actions / CI

Workflows live in `.github/workflows/`:

| Workflow | Purpose |
|---|---|
| `test.yml` | Runs ruff, mypy (non-blocking), and pytest on push/PR to `main` |
| `hassfest.yml` | Validates `manifest.json` and integration structure |
| `hacs.yml` | Validates HACS compliance |
| `release.yml` | Triggered by `v*` tags. Runs tests, verifies manifest version, creates zip, publishes GitHub Release |

All workflows set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as a transitional env var.

### Workflow Security Notes

- All workflows declare `permissions: contents: read` by default.
- `release.yml` grants `contents: write` only to the release job.
- `release.yml` uses a SHA-pinned `softprops/action-gh-release`.
- `release.yml` **does not push to `main`**; it reads the tag and creates a release from it.

---

## Release Process

1. Update `manifest.json` and `pyproject.toml` versions manually.
2. Update `CHANGELOG.md` with the new version section.
3. Commit and push to `main`.
4. Wait for CI on `main` to pass (`test.yml`, `hassfest.yml`, `hacs.yml`).
5. Create a lightweight tag from the current `main` HEAD:
   ```bash
   git tag vX.Y.Z
   ```
6. Push the tag:
   ```bash
   git push origin vX.Y.Z
   ```
7. `release.yml` runs automatically, verifies the manifest version matches the tag, and publishes the GitHub Release with `nature_remo.zip` attached.

### Moving an Existing Tag

If a tag was pushed but the release workflow failed, delete and recreate the tag:

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
git tag vX.Y.Z
git push origin vX.Y.Z
```

Avoid moving tags that have already been consumed by HACS users.

---

## Common Pitfalls

- **Stale `__pycache__`** — Delete `custom_components/nature_remo/__pycache__/` after major refactors before restarting Home Assistant.
- **Merge conflicts** — If the repo enters an unmerged state, resolve carefully and run tests before committing. Never leave `<<<<<<< HEAD` markers in Python files.
- **Version consistency** — `manifest.json`, `pyproject.toml`, and the release tag must all match. The release job verifies this.
- **Mypy noise** — Many type errors come from Home Assistant's generic entity APIs. Do not chase all of them; fix only the ones related to code you are changing.

---

## Communication

- Respond to the user in the same language they use (Japanese if they write in Japanese).
- Be concise. Avoid unnecessary explanations.
- When the user asks for changes that affect CI, workflows, or release process, update this file to keep it accurate.
