# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - Unreleased

### Changed
- Rebuilt integration from fork origin with a focus on testability and maintainability.
- Added comprehensive test suite.
- Added CI/CD workflows for tests, lint, HACS validation, Hassfest, and releases.

### Fixed
- Handle missing `X-Rate-Limit-Reset` header without crashing.
- Parse hexadecimal values in smart meter properties correctly.
