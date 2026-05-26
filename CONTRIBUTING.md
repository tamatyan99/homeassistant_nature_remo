# Contributing

Thank you for your interest in improving this Home Assistant custom integration.

## Development setup

1. Fork and clone this repository.
2. Create a Python 3.12 virtual environment and install test dependencies:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install pytest-homeassistant-custom-component
```

3. Run the test suite:

```bash
python -m pytest tests/ -v
```

All external API calls are mocked; no Nature Remo account or network access is required.

## Pull requests

1. Open an issue for significant changes or new features when possible.
2. Create a feature branch from `main`.
3. Keep changes focused and match existing code style.
4. Add or update tests when behavior changes.
5. Ensure `python -m pytest tests/ -v` passes before submitting.
6. Bump `custom_components/nature_remo/manifest.json` version on user-facing releases.

## Releases (maintainers)

1. Update `manifest.json` version, commit, and push to `main`.
2. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
3. Avoid force-pushing tags when possible to protect HACS users.

## Code guidelines

- Follow [Home Assistant development documentation](https://developers.home-assistant.io/docs/development_index) where applicable.
- Use English for log messages and code comments.
- Prefer translatable strings (`strings.json`, `translation_key`, `ServiceValidationError` with translation keys) for user-facing text.
- Do not commit `venv/` or `__pycache__/`.
