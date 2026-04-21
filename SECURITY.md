# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | Yes       |
| < 2.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in MonitorSnap, please report it
responsibly.

**Do not open a public issue.** Instead, use one of the following:

- [GitHub Security Advisories](https://github.com/GTRows/MonitorSnap/security/advisories/new) (preferred)
- Contact the maintainer directly through the email on their GitHub profile

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix or mitigation**: Depends on severity, but we aim for 30 days

## Scope

This policy covers:

- The Python backend (`display_presets/`)
- The Electron frontend (`electron-app/`)
- The HTTP server that bridges Electron to Python (localhost only)
- Registry and filesystem operations

## Known Design Decisions

- The Python HTTP server binds to `127.0.0.1` only and is not exposed to the network.
- The app uses Windows Display Configuration API via ctypes with no elevated privileges by default.
- All user data is stored locally in `%APPDATA%\MonitorSnap\`.
