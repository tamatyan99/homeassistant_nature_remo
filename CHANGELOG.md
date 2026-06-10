# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
