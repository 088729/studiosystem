# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, open an issue labeled `security` on the repository, or contact the
maintainers directly. Include:

- the version of `studiosystem-mcp` (`studiosystem-mcp --help` or package metadata)
- the transport in use (stdio / HTTP) and relevant configuration (redacted)
- reproduction steps and impact

## Scope notes

This server is a **credential-holding REST adapter**:

- It stores a Studio backend token (password / bearer / PAT mode) in memory.
- Write tools can modify mind maps, tasks, and wiki pages on the connected instance.
- HTTP transport should always run behind the outer bearer token
  (`STUDIO_MCP_MCP_TOKEN`) and, for non-loopback exposure, a TLS reverse proxy.

Hardening defaults:

- `STUDIO_MCP_READ_ONLY=true` registers read-only tools only — recommended for
  untrusted client experiments.
- The dedicated service account should carry least-privilege permissions
  (never `admin` / `sys:manage`).
- Audit logs mask credentials; still, treat audit files and `.env` as sensitive.

## Supported versions

| Version | Supported |
|---|---|
| latest | yes |
| older | no |
