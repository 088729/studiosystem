"""Live end-to-end test against a real Studio backend. MANUAL ONLY — never run in CI.

Spawns the real backend (uvicorn on 8302, needs local MongoDB), creates a
dedicated ``mcp-bot`` user, then exercises the MCP server two ways:

  Phase A — in-process MCPServer with the real HTTP transport (backend contract)
  Phase B — real stdio subprocess + mcp ClientSession (client-equivalent smoke)

Cleanup: created tasks / wiki pages / maps are removed via an admin REST
session; the backend process is always terminated in ``finally``.

Required env: ``ADMIN_INITIAL_PASSWORD`` — password of an admin account that
exists on the backend (used to create/clean up the bot user). Never hardcode.

Usage:  ADMIN_INITIAL_PASSWORD=*** .venv/Scripts/python scripts/e2e_live.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT.parent
BACKEND_DIR = WORKSPACE / "backend"
BACKEND_PY = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PY = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

BASE = "http://127.0.0.1:8302"
API = f"{BASE}/api/v1"
ADMIN = (os.environ.get("E2E_ADMIN_USER", "admin"), os.environ["ADMIN_INITIAL_PASSWORD"])
BOT = "mcp-bot"
BOT_PASSWORD = f"e2e-{uuid.uuid4().hex[:12]}!"

results: list[tuple[str, str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append(("PASS" if cond else "FAIL", name, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def admin_client() -> httpx.Client:
    c = httpx.Client(base_url=API, timeout=15)
    r = c.post("/common/auth/login", json={"username": ADMIN[0], "password": ADMIN[1]})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


def ensure_bot_user(admin: httpx.Client) -> None:
    """Fresh mcp-bot with least-privilege extra permissions (idempotent)."""
    admin.delete(f"/common/auth/users/{BOT}")  # 404 也无所谓，重建保证密码已知
    r = admin.post(
        "/common/auth/users",
        json={"username": BOT, "password": BOT_PASSWORD, "role_name": "viewer", "full_name": "MCP Bot (e2e)"},
    )
    r.raise_for_status()
    r = admin.patch(
        f"/common/auth/users/{BOT}/permissions",
        json={
            "role_name": "viewer",
            "extra": [
                "xmind:view", "xmind:edit",
                "task:view", "task:create", "task:edit", "task:delete",
                "wiki:view", "wiki:edit", "wiki:delete",
            ],
            "denied": [],
        },
    )
    r.raise_for_status()


async def wait_backend(proc: subprocess.Popen, timeout: float = 90) -> None:
    async with httpx.AsyncClient(base_url=BASE) as c:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"backend exited early (code {proc.returncode})")
            try:
                if (await c.get("/health", timeout=1.5)).status_code == 200:
                    return
            except httpx.TransportError:
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError("backend did not become healthy in time")


async def phase_a(admin: httpx.Client, created: dict) -> None:
    print("\nPhase A — in-process server, real HTTP transport")
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from studiosystem_mcp.server import build_server
    from studiosystem_mcp.settings import Settings

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            studio_base_url=BASE,
            auth_mode="password",
            username=BOT,
            password=BOT_PASSWORD,
            modules="case,task,wiki,git",
            audit_file=str(Path(tmp) / "audit.jsonl"),
            rate_limit_per_minute=0,  # 联调不受限流干扰
        )
        mcp, ctx = build_server(settings)
        try:
            async def call(tool: str, args: dict) -> dict:
                res = await mcp.call_tool(tool, args)
                return json.loads(res.content[0].text)

            # A1/A2 连通性与身份
            status = await call("studio_status", {})
            check("A1 studio_status", status.get("ok") is True, f"backend={status.get('backend', '?')}")
            me = await call("whoami", {})
            check(
                "A2 whoami == mcp-bot",
                me.get("username") == BOT and "wiki:edit" in me.get("permissions", []),
                f"role={me.get('role_name')} perms={len(me.get('permissions', []))}",
            )

            # A3 导图：建→读大纲
            map_id = None
            created_map = await call(
                "case_create_map",
                {"title": f"E2E 导图 {uuid.uuid4().hex[:6]}", "outline": "登录模块\n  正常登录\n  异常登录"},
            )
            if created_map.get("ok"):
                map_id = created_map["map"].get("id")
                created["maps"].append(map_id)
            got = await call("case_get_map", {"map_id": map_id}) if map_id else {}
            check("A3 case_create→get_map", bool(map_id) and "正常登录" in got.get("outline", ""), f"map={map_id}")

            # A4 任务：quick-add 创建 → 软删
            task = await call("task_create", {"text": "E2E 验证任务 @明天 !高"})
            task_id = (task.get("task_raw") or {}).get("id")
            if task_id:
                created["tasks"].append(task_id)
            check(
                "A4 task_create quick-add",
                task.get("ok") is True and (task.get("task_raw") or {}).get("priority") == 3,
                f"task={task_id}",
            )
            if task_id:
                deleted = await call("task_delete", {"task_id": task_id, "mode": "soft"})
                check("A4b task soft delete", deleted.get("ok") is True)

            # A5/A6 Wiki：建页 → 两阶段覆盖写 → 历史含自定义 commit message
            vault_id = None
            vaults = await call("wiki_list_vaults", {})
            items = vaults.get("vaults") or []
            if items:
                vault_id = items[0]["id"]
            page_path = f"mcp-e2e/{uuid.uuid4().hex[:8]}.md"
            created_page = (
                await call("wiki_create_page", {"vault_id": vault_id, "path": page_path, "content": "# E2E 首页"})
                if vault_id else {}
            )
            check("A5 wiki_create_page", created_page.get("ok") is True, f"vault={vault_id} path={page_path}")
            if vault_id:
                first = await call(
                    "wiki_write_page",
                    {
                        "vault_id": vault_id,
                        "path": page_path,
                        "content": "# E2E 首页\n\n覆盖内容",
                        "overwrite": True,
                        "message": "test(e2e): 覆盖写入",
                    },
                )
                token = first.get("confirm_token")
                second = await call(
                    "wiki_write_page",
                    {
                        "vault_id": vault_id,
                        "path": page_path,
                        "content": "# E2E 首页\n\n覆盖内容",
                        "overwrite": True,
                        "message": "test(e2e): 覆盖写入",
                        "confirm_token": token,
                    },
                ) if token else {}
                hist = await call("wiki_history", {"vault_id": vault_id, "path": page_path})
                entries = hist.get("entries") or []
                committed = second.get("committed") is True and any(
                    "test(e2e)" in (e.get("message") or "") for e in entries
                )
                check("A6 wiki_write_page 两阶段+显式 commit", committed, f"committed={second.get('committed')}")
                created["pages"].append((vault_id, page_path))

            # A7 git 域只读
            if vault_id:
                vs = await call("vault_status", {"vault_id": vault_id})
                check("A7 vault_status", vs.get("ok") is True, f"changes={len(vs.get('changes') or [])}")

            # A8 审计落盘：无凭据明文，且掩码器生效（confirm_token 含 token 键名 → 打码）
            audit_text = (Path(tmp) / "audit.jsonl").read_text(encoding="utf-8")
            check(
                "A8 审计无密码明文且掩码生效",
                BOT_PASSWORD not in audit_text and '"confirm_token": "***"' in audit_text,
            )
        finally:
            await ctx.aclose()


async def phase_b(created: dict) -> None:
    print("\nPhase B — real stdio subprocess + MCP client session")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "STUDIO_MCP_STUDIO_BASE_URL": BASE,
        "STUDIO_MCP_AUTH_MODE": "password",
        "STUDIO_MCP_USERNAME": BOT,
        "STUDIO_MCP_PASSWORD": BOT_PASSWORD,
        "STUDIO_MCP_MODULES": "case,task,wiki",
        "STUDIO_MCP_RATE_LIMIT_PER_MINUTE": "0",
        "STUDIO_MCP_LOG_LEVEL": "WARNING",
    }
    params = StdioServerParameters(
        command=str(VENV_PY),
        args=["-m", "studiosystem_mcp", "--transport", "stdio"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            check("B1 stdio tools/list", "studio_status" in names and "wiki_write_page" in names, f"tools={len(names)}")
            res = await session.call_tool("studio_status", {})
            payload = json.loads(res.content[0].text)
            check("B2 stdio studio_status", payload.get("ok") is True)
            res = await session.call_tool("task_create", {"text": "E2E stdio 任务 @明天"})
            payload = json.loads(res.content[0].text)
            task_id = (payload.get("task_raw") or {}).get("id")
            if task_id:
                created["tasks"].append(task_id)
            check("B3 stdio task_create", payload.get("ok") is True and task_id, f"task={task_id}")
            assert session._initialize_result is not None  # 协议握手完成


async def main() -> int:
    created = {"tasks": [], "pages": [], "maps": []}
    admin = None
    backend = None
    try:
        print("Starting backend (uvicorn :8302) …")
        backend = subprocess.Popen(
            [str(BACKEND_PY), "-m", "uvicorn", "app.main:app", "--port", "8302", "--log-level", "warning"],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        await wait_backend(backend)
        print("Backend healthy.")

        admin = admin_client()
        ensure_bot_user(admin)
        print(f"Bot user '{BOT}' ready (least-privilege permissions).")

        await phase_a(admin, created)
        await phase_b(created)
    except Exception as exc:  # noqa: BLE001 - report and still cleanup
        results.append(("FAIL", "harness", f"{type(exc).__name__}: {exc}"))
        print(f"  [FAIL] harness — {exc}")
    finally:
        if admin is not None:
            for task_id in created["tasks"]:
                try:
                    admin.delete(f"/task/tasks/{task_id}")
                except Exception:
                    pass
            for vault_id, path in created["pages"]:
                try:
                    admin.delete(f"/wiki/vaults/{vault_id}/pages", params={"path": path})
                except Exception:
                    pass
            for map_id in created["maps"]:
                try:
                    admin.delete(f"/case/maps/{map_id}")
                except Exception:
                    pass
            admin.close()
        if backend is not None:
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()

    failed = [r for r in results if r[0] == "FAIL"]
    print(f"\n{'=' * 56}\nLive E2E: {len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
