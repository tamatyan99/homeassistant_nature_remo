# Security Policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please report security issues privately via [GitHub Security Advisories](https://github.com/tamatyan99/homeassistant_nature_remo/security/advisories/new) rather than opening a public issue.

## Sensitive data

- **API keys** are stored in Home Assistant config entries. Never commit real API keys or share them in issue reports.
- **Diagnostics** exports mask API keys, serial numbers, MAC addresses, and device names.
- **Local IP mode** sends IR commands over unencrypted HTTP on your LAN. Only enable this on trusted networks when you understand the risk.

## Recommendations for users

- Use Home Assistant secrets or the UI to store your Nature Remo API key.
- Restrict network access to your Nature Remo device if using the local IP option.
- Keep Home Assistant and this integration up to date.
