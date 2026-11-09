# Contributing

Thanks for your interest in improving studiosystem-mcp!

## Development setup

```bash
uv venv .venv
uv pip install -e ".[dev]"
pytest
ruff check .
```

Tests use `httpx.MockTransport` — no real Studio backend is required.

## Ground rules

- **Never commit credentials or internal network values.** CI runs a
  zero-residue scan (`scripts/zero_residue_scan.py`); hits fail the build.
  Keep examples on `localhost` / `example.com` / placeholder tokens.
- The backend contract is documented in code comments and mirrored in
  `tests/conftest.py` stubs; update both when adding endpoints.
- Tool naming: `<domain>_<verb>` with domain prefixes (`case_`, `task_`,
  `wiki_`, `focus_`…).
- New write tools must go through the confirm flow (`policy/confirm.py`) and be
  registered with correct `ToolMeta` (read_only / destructive).
- `tools/list` must stay deterministically sorted; the server enforces this —
  keep it that way when adding tools.

## Pull requests

- One logical change per PR, tests included.
- Ruff clean: `ruff check .`
- If you add a dependency, note its license in `LICENSE` third-party notices.
