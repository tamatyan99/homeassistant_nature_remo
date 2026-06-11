# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.7] - 2026-06-10

### Fixed
- **Swagger spec compliance** (`https://swagger.nature.global/`):
  - Climate payloads now always include `temperature_unit` per the `AirConParams_` schema (previously missing on `turn_off`).
  - Signal send (`POST /signals/{signalid}/send`) now explicitly sends an empty body `{}` matching the `EmptyObject` request body schema.
  - Hardened null-safe handling for all nullable Swagger fields: `DeviceResponse.newest_events`, `ApplianceResponse.device`, `ApplianceResponse.light`, `ApplianceResponse.settings`, and `SmartMeterResponse.echonetlite_properties`.
  - Fixed `light.py` crash when the API returns `null` for `light.state` or `light.buttons`.
- **P0** `coordinator.py` no longer swallows `asyncio.CancelledError`; service handlers in `__init__.py` also re-raise it instead of converting it to a generic `HomeAssistantError`.
- **P1** Authentication failures (`NatureRemoAuthError`) now consistently propagate as `ConfigEntryAuthFailed` in `switch`, `remote`, `button`, and `select` platforms, and in custom service handlers.
- **P1** `switch` and `remote` now roll back optimistic state changes when the API call fails.
- **P1** `remote.send_command` raises `ServiceValidationError` for unknown commands instead of silently ignoring them.
- **P1** Climate preset mode is now refreshed from coordinator data and no longer drifts when changed outside Home Assistant.
- **P1** Climate `async_set_preset_mode` no longer silently swallows `HomeAssistantError` for non-eco presets.
- **P1** `send_local_ir_message` now requires `local_ip` and raises `ValueError` when missing, preventing unauthenticated cloud calls.
- **P1** Automatic 429 retry is restricted to `GET` requests to avoid double-firing non-idempotent `POST` commands.
- **P1** Transport-level `ClientError` and HTTP 502/503/504 responses are now retried with capped exponential backoff.
- **P1** Re-authenticating with the same API key now succeeds instead of aborting with `already_configured`.
- **P1** Diagnostics now redact the configured `local_ip`.
- **P1** Corrupt `update_interval` / `motion_threshold_minutes` option values no longer crash setup; they fall back to defaults with a warning.
- **P1** Domain-level custom services are registered only once and are removed only after the last config entry is unloaded.
- **P2** Unified climate optimistic-update/rollback logic into `_apply_climate_command` helper.
- **P2** Extracted shared IR command/power-id builder (`build_ir_commands`) to reduce duplication between `switch` and `remote`.

### Added
- `User-Agent: HomeAssistant-NatureRemo/0.6.6` header on cloud API requests.
- Translation keys for common service/entity errors in `strings.json`.
- Coverage configuration in `pyproject.toml` (branch coverage, 80% fail-under).

### Tests
- Added 26 new tests covering: climate `turn_on`/`turn_off`/`set_swing_mode`, external temperature/humidity sensor override/fallback, coordinator-driven preset sync, service error paths, reauth same-key, diagnostics `local_ip` redaction, options-flow stale per-device key removal, API failure paths, and `mock_api` spec hardening.

## [0.6.5] - 2026-06-10

### Fixed
- Official Nature API compliance fixes reviewed against https://developer.nature.global/:
  - Split Cloud API and Local API request headers. Local API calls now send the required `X-Requested-With` header and no longer send the `Authorization: Bearer` token, which is only valid for Cloud endpoints.
  - Raised the minimum cloud update interval from 10 s to 30 s so the default refresh path respects the documented rate limit of 30 requests per 5 minutes.
  - Released the cloud request lock while waiting during 429 back-off, preventing the lock from blocking other callers for the entire retry delay.
  - Added `temperature_unit=c` to all climate control payloads that send `operation_mode` or `temperature`, matching the official API specification.
- `api.learn_signal` now logs a warning because it uses the undocumented `/appliances/{id}/IR` endpoint. This preserves backward compatibility while informing users that the call is not officially supported.

## [0.6.4] - 2026-06-10

### Added
- Comprehensive options-flow test coverage, including:
  - validation of schema fields (`update_interval`, `motion_threshold_minutes`, `local_ip`)
  - valid/invalid submissions
  - per-device external temperature/humidity selector generation and persistence

### Changed
- Refactored AC preset (`eco` / `none`) logic in `climate.py` and `select.py` to share a single helper (`async_apply_ac_preset`), removing duplicated payload construction and API calls.

### Fixed
- Resolved unresolved Git merge conflicts that had left the integration syntactically broken in `__init__.py`, `api.py`, `climate.py`, `light.py`, `sensor.py`, `event.py`, and `tests/test_api.py`.
- Hardened `climate.format_temperature` to safely handle `int` and non-numeric inputs.
- Strengthened diagnostics redaction so nested PII (e.g. inside `signals`, `device`, `light.buttons`) is masked recursively.
- Removed unused `_request` helper from `api.py`.

### Security
- Diagnostics downloads now mask sensitive keys (`id`, `name`, `nickname`, `device_id`, `appliance_id`, `serial_number`, `mac_address`) recursively across devices and appliances.
