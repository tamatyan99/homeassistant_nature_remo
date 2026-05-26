# Contributing

Thank you for contributing to the Nature Remo Home Assistant integration.

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

## Pull requests

- Open an issue first for large features or breaking changes.
- Keep changes focused and include tests for behavior changes.
- Run `python -m pytest tests/ -v` before submitting.
- Bump `manifest.json` version on releases.

## Code style

- Follow existing patterns in `custom_components/nature_remo/`.
- Use type hints for new public functions and entity methods.
- Avoid broad `except Exception` handlers unless re-raising as a specific error.
