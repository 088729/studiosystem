# studiosystem-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2026--07--28%20%2F%202025--11--25-blue)](https://modelcontextprotocol.io)

> Part of the [Studio System](../README.md) monorepo — this directory (`mcp-server/`) is a self-contained Python package with its own dev venv, tests, and CI workflow templates. The dev master lives in a private repo; this copy is the open-source export.

[MCP](https://modelcontextprotocol.io) server for **Studio System** — a thin, safety-first REST adapter that lets AI clients (Claude, Kimi Work, Cursor, WorkBuddy…) work with your Studio instance:

- **Mind maps (use cases)**: list folders/maps, read a map as a **text outline** instead of raw JSON
- **Tasks**: list/query tasks, lists, tags, filters with high-level semantics
- **Wiki**: vaults, page tree, read pages, full-text search / backlinks / graph

It talks to the existing `/api/v1` REST API over HTTP — **no database access, no backend code changes** — and inherits the backend's JWT + RBAC permissions.

> ⚠️ **This server holds writable credentials.** Run it in a trusted environment. For read-only exploration set `STUDIO_MCP_READ_ONLY=true`.

## Quick start

Not on PyPI — install straight from the monorepo with `uv` (the `#subdirectory` fragment points pip/uv at this folder):

```bash
# stdio (local client integration)
uvx --from "git+https://github.com/088729/studiosystem@main#subdirectory=mcp-server" studiosystem-mcp

# or HTTP transport
uvx --from "git+https://github.com/088729/studiosystem@main#subdirectory=mcp-server" studiosystem-mcp --transport http --port 8303
```

Minimal client config (e.g. Claude Desktop / Kimi Work):

```json
{
  "mcpServers": {
    "studio": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/088729/studiosystem@main#subdirectory=mcp-server",
        "studiosystem-mcp"
      ],
      "env": {
        "STUDIO_BASE_URL": "http://127.0.0.1:8302",
        "STUDIO_MCP_AUTH_MODE": "password",
        "STUDIO_MCP_USERNAME": "mcp-bot",
        "STUDIO_MCP_PASSWORD": "your-password"
      }
    }
  }
}
```

Remote HTTP mode:

```json
{
  "mcpServers": {
    "studio": {
      "url": "http://your-host:8303/mcp",
      "headers": { "Authorization": "Bearer <mcp-token>" }
    }
  }
}
```

## Authentication modes (`STUDIO_MCP_AUTH_MODE`)

| Mode | Config | Behavior |
|---|---|---|
| `password` | `STUDIO_MCP_USERNAME` / `STUDIO_MCP_PASSWORD` | Logs in via `POST /common/auth/login` with `remember_me=true` (30-day JWT), caches in memory, re-logins on 401 and retries once |
| `bearer` | `STUDIO_MCP_TOKEN` or `STUDIO_MCP_TOKEN_FILE` | Uses a long-lived JWT injected by the deployer; never persisted |
| `pat` | `STUDIO_MCP_PAT` | Reserved for a future backend Personal Access Token (P3 backend enhancement) |

Use a **dedicated least-privilege service account** (e.g. `mcp-bot` with the `viewer` role plus explicit `extra_permissions`) — never `admin`. See [.env.example](.env.example) and [config.example.yaml](config.example.yaml) for the full configuration surface.

## Configuration

Three layers, highest wins: environment variables (`STUDIO_MCP_*`) → `config.yaml` (path in `STUDIO_MCP_CONFIG`) → built-in defaults. See [.env.example](.env.example) and [config.example.yaml](config.example.yaml) for the full list.

Key knobs:

| Setting | Default | Notes |
|---|---|---|
| `STUDIO_BASE_URL` | `http://127.0.0.1:8302` | Backend URL, **without** `/api/v1` |
| `STUDIO_MCP_MODULES` | `case,task,wiki` | Capability domains; disabled domains' tools are not registered at all |
| `STUDIO_MCP_READ_ONLY` | `false` | When `true`, no write tools are registered |
| `STUDIO_MCP_ALLOWED_TOOLS` / `STUDIO_MCP_DENIED_TOOLS` | — | Fine-grained allow/deny lists (deny wins) |
| `STUDIO_MCP_CONFIRM_MODE` | `auto` | `auto` (protocol-native elicitation when the client supports it, else confirm token) / `token` / `none` |
| `STUDIO_MCP_TRANSPORT` | `stdio` | `stdio` / `http` |
| `STUDIO_MCP_HOST` / `STUDIO_MCP_PORT` | `127.0.0.1` / `8303` | HTTP listen address. Default is loopback-only; exposing beyond localhost requires the outer bearer token below |
| `STUDIO_MCP_MCP_TOKEN` | — | Outer bearer token for HTTP mode (shared-secret style). Empty = loopback-only + warning (`insecure_dev_only`) |
| `STUDIO_MCP_MAX_RESULT_ITEMS` | `20` | Result trimming threshold to protect context |
| `STUDIO_MCP_DEFAULT_VAULT_ID` / `STUDIO_MCP_DEFAULT_WIKI_PATH` | — / `reports/{date}.md` | Workflow targets; `{date}` = local date (Asia/Shanghai default via `TZ_OFFSET_MINUTES`) |
| `STUDIO_MCP_TEMPLATES_DIR` | — | Custom Jinja2 template dir overriding builtin `weekly_report.md.j2` / `testcase_spec.md.j2` / `retro.md.j2` |
| `STUDIO_MCP_ALLOW_ADMIN` | `false` | **Admin domain master switch** (`admin_*` tools). Requires `READ_ONLY=false`; backend still enforces `sys:manage` on every admin endpoint |
| `STUDIO_MCP_RATE_LIMIT_PER_MINUTE` | `30` | Token-bucket cap on tool calls per minute (per identity); `<=0` disables. Protects the backend from model loop storms |
| `STUDIO_MCP_LOG_LEVEL` / `STUDIO_MCP_AUDIT_FILE` | `INFO` / — | Audit JSONL path; empty = stderr only (stdio mode **must** keep stdout protocol-clean) |

## Tools

**System**: `studio_status`, `studio_capabilities`, `whoami` (permissions self-check)

**Case**: read — `case_list_folders`, `case_list_maps`, `case_get_map` (text outline, `source=draft|published|version:N`); write — `case_create_map` (outline→tree), `case_edit_map` (node patches add/update/delete/move; lock→read→version-CAS→snapshot→unlock closed loop; forced two-phase confirm), `case_save_draft` (async draft), `case_versions` (list / rollback; rollback requires `ALLOW_DESTRUCTIVE` + confirm)

**Task**: read — `task_list_context`, `task_list_tasks`, `task_get_task`; write — `task_create` (quick-add `@明天 !高 ~回归 #清单` + idempotency key), `task_update` (PATCH fields / `action=complete|uncomplete|skip`), `task_delete` (`soft|restore|purge`; purge requires `ALLOW_DESTRUCTIVE` + confirm), `task_batch` (forced confirm)

**Wiki**: read — `wiki_list_vaults`, `wiki_tree`, `wiki_read_page`, `wiki_search` (search / backlinks / graph); write (P2) — `wiki_create_page` (409-safe one step), `wiki_write_page` (read-before-write + diff preview + lock→PUT→explicit commit→release; forced confirm; refuses blind overwrite), `wiki_history` (`list|diff|revert`; revert requires `ALLOW_DESTRUCTIVE` + confirm)

**Analytics / Focus / Habits**: read — `task_overview`, `task_summary_markdown` (日报/周报素材), `focus_status`, `focus_report`, `habit_today`, `habit_week`, `habit_stats`; write (P2, one step) — `focus_start`, `focus_pause`, `focus_resume`, `focus_finish`, `focus_abandon`, `habit_checkin`, `habit_skip`, `habit_un_checkin`

**Git (P2)**: `vault_status`, `page_history`, `page_diff`, `page_revert` (requires `ALLOW_DESTRUCTIVE` + confirm), `vault_pull` / `vault_push` (confirm; push also `ALLOW_DESTRUCTIVE`), `vault_commit` (confirm, custom message), `wiki_reindex` (async; poll `vault_status.rebuild`)

**Collab (P2)**: `task_comment` (`list|add`), `calendar_range`, `pending_reminders`, `reminder_ack` (ack / snooze), `share_members` (`list|add`)

**Workflow (P2)**: `generate_wiki_from_tasks` (summary → Jinja2 → page + commit), `generate_wiki_from_case` (map outline → testcase_spec + backlinks), `case_outline_to_tasks` (leaf nodes → tasks with `case_map_id`/`case_node_id` backfill; forced confirm)

**Prompts (P2)**: `weekly_report`, `testcase_spec`, `retro`, `case_review`, `standup` — safety-constrained prompt templates (preview diff before any write).

**Admin (P3, default OFF)**: `admin_user_list` / `admin_role_list` / `admin_permission_list` (read); `admin_user_create` / `admin_user_update` (`permissions|active|job_scope`) / `admin_user_delete` / `admin_batch_permissions` / `admin_role_create` / `admin_role_update` / `admin_role_delete` / `admin_permission_create` / `admin_permission_delete` (all forced-confirm). Triple-gated: `ALLOW_ADMIN=true` + `READ_ONLY=false` + backend `sys:manage`. Client-side guardrails: cannot delete/deactivate the currently authenticated user; passwords are masked in audit logs and never echoed in previews/results. **Treat this domain as holding the keys to the kingdom — enable only for admin scenarios, and prefer a least-privilege `mcp-bot` account for everyday use.**

Write tools follow risk-tiered confirmation (Q4): irreversible/whole-tree operations (`case_edit_map`, rollback, purge, batch) return a preview + `confirm_token` and execute only when the token is presented; low-risk operations run in one step (`dry_run=true` previews). `STUDIO_MCP_CONFIRM_MODE=none` disables forced confirmation for unattended pipelines.

## Design notes

- **Semantic traps are absorbed here, not exposed to the model**: draft-vs-snapshot duality, whole-tree overwrite on save, 1-minute edit lock TTL, `due_at` field names, last-write-wins APIs.
- **Error normalization**: backend `{"detail": {"code","message"}}` becomes a readable message + `code` + suggested action.
- **Protocol versions**: targets MCP 2026-07-28 with 2025-11-25 as compatibility baseline; capabilities are declared via `server/discover` when the client requests it, with graceful degradation.
- **Auditing**: every call is logged as JSONL (credentials masked).

## Development

```bash
uv venv .venv && uv pip install -e ".[dev]"
pytest            # uses httpx.MockTransport — no real backend needed
ruff check .
python scripts/zero_residue_scan.py   # internal-value leak gate (runs in CI too)
```

## Release

In the monorepo this package is versioned with the main project tags; `mcp-server/.github/workflows/` holds the CI / tag-release workflow templates (ruff, zero-residue scan, pytest, wheel build + smoke-install, protocol matrix, commented PyPI step) — they activate if this directory is ever split back out into a standalone repo. Protocol compatibility is guarded by `tests/test_protocol_matrix.py` against both supported protocol versions (2026-07-28 / 2025-11-25).

## Security

See [SECURITY.md](SECURITY.md). Reporting: please open an issue labeled `security`.

## License

MIT — see [LICENSE](LICENSE).
