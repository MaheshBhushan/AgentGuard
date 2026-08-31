# Security policy

## Supported versions

AgentGuard is in early development; security fixes are applied to the latest revision only until releases begin.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting for this repository. If that facility is unavailable, contact the maintainers privately through the repository owner's published security contact.

Include the affected revision, platform, reproduction steps, impact, and any suggested mitigation. Avoid including live credentials or third-party private data. Maintainers will acknowledge a complete report as soon as practical and coordinate disclosure after a fix is available.

AgentGuard invokes third-party tools against untrusted repositories. Reports should redact secrets, commands must never use a shell, and contributors must treat analyzer output as untrusted text.
