# AGENTS.md

This file contains context and conventions for AI agents working on this project.

## Project Overview

- **Name**: Nature Remo Home Assistant Custom Integration
- **Domain**: `nature_remo`
- **Current Version**: `0.3.0` (in development)
- **Repository**: https://github.com/tamatyan99/homeassistant_nature_remo
- **Fork Origin**: https://github.com/NaNaLinks/homeassistant_nature_remo

## Development Philosophy

This integration was reset to the fork origin and is being rebuilt with a focus on:

1. **Testability first** — write tests before or alongside code changes
2. **Official API compliance** — follow https://developer.nature.global/ and https://swagger.nature.global/
3. **Minimal, clean code** — avoid workarounds and duplication
4. **HACS readiness** — aim for default HACS store inclusion

## Environment

- **Python**: 3.12
- **Home Assistant**: minimum 2023.8.0
- **Package manager**: pip with `pyproject.toml`
- **Linter**: ruff
- **Test runner**: pytest with `pytest-homeassistant-custom-component`

## Common Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v --tb=short --timeout=120

# Run lint
python -m ruff check custom_components/nature_remo tests

# Run with coverage
python -m pytest tests/ --cov=custom_components/nature_remo --cov-report=term-missing
```

## Code Conventions

- Use English for code, comments, and docstrings.
- Follow Google docstring convention.
- Use `async`/`await` for I/O-bound operations.
- Use `CoordinatorEntity` for entities that depend on coordinator data.
- Use `DataUpdateCoordinator` for periodic API updates.
- Prefer static `_attr_*` class attributes over properties when values do not change.
- Handle nullable API fields gracefully.
- Use `_LOGGER.debug` for verbose output, `_LOGGER.warning` for recoverable issues,
  `_LOGGER.error` for failures.

## API Conventions

- Cloud API base URL: `https://api.nature.global/1`
- Always send `Authorization: Bearer <token>` for cloud requests.
- Climate control payloads must include `temperature_unit=c` when sending temperature or mode.
- Local API uses `X-Requested-With` header and no Bearer token.
- Respect rate limits: 30 requests per 5 minutes for the cloud API.

## Release Process

1. Update `custom_components/nature_remo/manifest.json` version.
2. Update `CHANGELOG.md`.
3. Ensure all tests pass and ruff is clean.
4. Commit and tag with `v<version>`.
5. Push the tag to trigger the release workflow.
6. Verify the GitHub Release includes `nature_remo.zip`.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the current development plan.
