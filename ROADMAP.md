# Nature Remo - Development Roadmap

This document outlines the plan to rebuild the Nature Remo Home Assistant custom integration from the fork origin (NaNaLinks v0.2.3) into a clean, tested, and HACS-ready integration.

## Status

- `main` branch reset to fork origin `NaNaLinks/homeassistant_nature_remo` (v0.2.3)
- Previous releases (`v0.6.x`) deleted from GitHub
- Development will continue as **v0.3.0**

## Goals

1. Stable, well-tested integration
2. Clean architecture without legacy workarounds
3. HACS default store eligibility
4. Official Nature API compliance

---

## Phase 1: Foundation

### Development Environment
- [ ] Create `pyproject.toml` with dependencies, dev-dependencies, pytest, ruff, and coverage config
- [ ] Create `requirements.txt` and `requirements-dev.txt`
- [ ] Set up `pytest.ini` / `setup.cfg` if needed
- [ ] Verify local test execution passes

### Test Infrastructure
- [ ] Create `tests/conftest.py` with:
  - Mock Home Assistant instance fixture
  - Mock NatureRemoAPI fixture
  - Sample device/appliance data fixtures
  - Config entry fixture
- [ ] Add `tests/__init__.py`

### CI/CD
- [ ] Restore `.github/workflows/test.yml`
- [ ] Restore `.github/workflows/ruff.yml` (or include in test.yml)
- [ ] Restore `.github/workflows/hacs.yml`
- [ ] Restore `.github/workflows/hassfest.yml`
- [ ] Restore `.github/workflows/release.yml`
- [ ] Pin action SHAs for security

### Project Files
- [ ] Update `manifest.json`:
  - Keep `config_flow: true`
  - Add `integration_type: "hub"`
  - Keep `iot_class: "cloud_polling"`
  - Update `codeowners`
  - Keep version in sync with releases
- [ ] Update `hacs.json`:
  - Set `homeassistant` minimum version
  - Set `zip_release: true` and `filename: "nature_remo.zip"`
  - Set `render_readme: true`
- [ ] Update `README.md` installation instructions
- [ ] Update `CHANGELOG.md` with new v0.3.0 section
- [ ] Create/Update `AGENTS.md` with development conventions

---

## Phase 2: Test Coverage for Existing Code

Write tests for the fork-origin code **before** refactoring.

- [ ] `tests/test_api.py`
  - API client initialization
  - GET /devices
  - GET /appliances
  - POST /appliances/{id}/aircon_settings
  - POST /appliances/{id}/light
  - POST /signals/{id}/send
  - Smart meter property parsing
  - Error handling (401, 429, 500, timeout)
- [ ] `tests/test_coordinator.py`
  - Data parsing for devices
  - Data parsing for appliances (AC, LIGHT, IR, EL_SMART_METER)
  - Update failure handling
- [ ] `tests/test_config_flow.py`
  - User step with valid API key
  - User step with invalid API key
- [ ] `tests/test_options_flow.py`
  - Options form generation
  - Options submission
- [ ] `tests/test_init.py`
  - Setup entry success
  - Unload entry
  - Custom service registration
- [ ] Platform tests
  - `tests/test_climate.py`
  - `tests/test_light.py`
  - `tests/test_sensor.py`
  - `tests/test_remote.py`

Target: **>80% branch coverage** before Phase 3.

---

## Phase 3: Code Refactoring

### API Client (`api.py`)
- [ ] Use a single shared `aiohttp.ClientSession`
- [ ] Add `async_get_clientsession` integration
- [ ] Implement proper retry logic for 429, 502, 503, 504
- [ ] Add rate-limit logging
- [ ] Add `NatureRemoAuthError` for 401
- [ ] Add `NatureRemoAPIError` for other failures
- [ ] Use `temperature_unit=c` for all climate payloads
- [ ] Add local API support with correct headers

### Coordinator (`coordinator.py`)
- [ ] Null-safe data parsing
- [ ] Separate device/appliance parsing into helper methods
- [ ] Handle missing or malformed API responses
- [ ] Store parsed data in a stable structure

### Entities
- [ ] Refactor `climate.py`:
  - Use `CoordinatorEntity`
  - Static `supported_features` where possible
  - External sensor override
  - Proper temperature formatting
  - Preset mode support (eco)
- [ ] Refactor `light.py`:
  - Use `CoordinatorEntity`
  - Effect list from API
  - Optimistic state with rollback
- [ ] Refactor `sensor.py`:
  - Split into separate platform files if needed
  - Use `SensorEntityDescription`
  - Configurable motion threshold
- [ ] Refactor `remote.py`:
  - Power on/off command detection
  - Service validation for unknown commands
- [ ] Add missing platforms:
  - `switch.py` (on/off toggle for appliances with power signals)
  - `binary_sensor.py` (motion detection)
  - `event.py` (motion detected events)
  - `button.py` (learn IR signal, refresh data)
  - `select.py` (light mode and AC preset selectors)

### Services
- [ ] Register custom services once at domain level
- [ ] Add `services.yaml`
- [ ] Implement `send_light_mode`
- [ ] Implement `learn_signal`

### Init
- [ ] Register services only once
- [ ] Clean up services on last config entry unload
- [ ] Store entities in `hass.data` for service handlers

---

## Phase 4: HACS Readiness

- [ ] Validate integration with HACS Action
- [ ] Validate integration with Hassfest Action
- [ ] Ensure `brands` directory or HACS brand reference
- [ ] Check `strings.json` translations
- [ ] Check `services.yaml` format
- [ ] Create release workflow that builds `nature_remo.zip`

### HACS Default Store Submission
- [ ] Fork `hacs/default`
- [ ] Add `tamatyan99/homeassistant_nature_remo` to `integration` file
- [ ] Open Pull Request
- [ ] Respond to review feedback
- [ ] Update README to remove "Custom repository required" note after merge

---

## Phase 5: Release v0.3.0

- [ ] Final test run with 100% of tests passing
- [ ] Final ruff check clean
- [ ] Final HACS/Hassfest validation clean
- [ ] Update `manifest.json` version to `0.3.0`
- [ ] Update `CHANGELOG.md`
- [ ] Build `nature_remo.zip`
- [ ] Commit and tag `v0.3.0`
- [ ] Push tag to trigger release workflow
- [ ] Verify GitHub Release with zip asset

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/).

- `v0.3.0` — Rebuilt foundation with tests and HACS readiness
- Subsequent patches `v0.3.1`, `v0.3.2`, etc. for bug fixes
- `v0.4.0` for future feature releases
