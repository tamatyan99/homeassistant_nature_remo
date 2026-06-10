# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
