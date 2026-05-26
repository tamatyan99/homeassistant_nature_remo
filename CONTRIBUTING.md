# Contributing

Thank you for your interest in improving the Nature Remo Home Assistant integration.

## Development setup

1. Clone this repository.
2. Create a virtual environment with Python 3.12:

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

- Keep changes focused on a single concern.
- Run tests before submitting.
- Update `manifest.json` version when releasing a new version for HACS cache invalidation.
- Do not commit `venv/` or `__pycache__/`.

## Releases (maintainers)

1. Bump `custom_components/nature_remo/manifest.json` version, commit, and push to `main`.
2. Create and push a lightweight tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
3. If a tag must be moved, delete it locally and remotely first, then recreate it.

## Code style

This project has no configured linter. Follow existing patterns in `custom_components/nature_remo/` and Home Assistant integration best practices.
