"""Shared fixtures: settings with in-memory transports, fake backend dispatcher."""

from __future__ import annotations

import json

import httpx
import pytest

from studiosystem_mcp.settings import Settings

FAKE_TOKEN = "fake-jwt-token"


def make_settings(**overrides) -> Settings:
    params = {
        "studio_base_url": "http://127.0.0.1:8302",
        "auth_mode": "bearer",
        "token": FAKE_TOKEN,
        "_settings_sources": None,
    }
    params.update(overrides)
    return Settings(**{k: v for k, v in params.items() if k != "_settings_sources"})


class FakeBackend:
    """Minimal in-memory simulation of the Studio backend contract."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.fail_health = False
        self.lock_conflict = False
        self.cas_conflict = False
        self.page_conflict = False  # wiki 页被他人锁定
        self.put_conflict = False  # 仅 PUT content 失败（锁已拿到），测 release 兜底
        self.rebuild_running = False
        self.pages: dict[str, str] = {"docs/index.md": "# 首页\n\n你好"}
        self.page_locks: dict[str, str] = {}
        self.focus_sessions: dict[str, dict] = {}
        self.comments: dict[str, list] = {}
        self.members: dict[str, list] = {"l1": [{"username": "mcp-bot", "role": "owner"}]}
        self.users: dict[str, dict] = {
            "mcp-bot": {
                "username": "mcp-bot",
                "role_name": "viewer",
                "perms": ["xmind:view", "task:view", "wiki:view"],
                "full_name": "MCP Bot",
                "email": None,
                "department": None,
                "job_scope": None,
                "is_active": True,
                "last_login_at": None,
                "created_at": "2026-11-01T08:00:00",
            },
            "tester": {
                "username": "tester",
                "role_name": "tester",
                "perms": ["xmind:view", "task:view"],
                "full_name": "测试员",
                "email": None,
                "department": None,
                "job_scope": None,
                "is_active": True,
                "last_login_at": None,
                "created_at": "2026-11-01T08:00:00",
            },
        }
        self.roles: dict[str, dict] = {
            "viewer": {"name": "viewer", "permissions": ["task:view"], "description": "内置只读", "is_builtin": True},
            "tester": {"name": "tester", "permissions": ["xmind:view", "task:view"], "description": "测试", "is_builtin": False},
        }
        self.permission_keys: list[dict] = [
            {"key": "task:view", "app_id": "task", "builtin": True},
            {"key": "wiki:edit", "app_id": "wiki", "builtin": True},
        ]
        self.maps = {
            "map1": {
                "id": "map1",
                "title": "登录模块",
                "owner": "tester",
                "folder_id": None,
                "current_version": 3,
                "created_at": "2026-11-01T08:00:00",
                "last_modified_at": "2026-11-08T08:00:00",
                "temp_content": {"root": {"data": {"text": "登录模块(草稿)", "uid": "root"}, "children": []}},
                "latest_root": {
                    "root": {
                        "data": {"text": "登录模块", "uid": "root", "expand": True},
                        "children": [
                            {
                                "data": {"text": "正常登录", "uid": "n1"},
                                "children": [
                                    {"data": {"text": "输入正确账号密码", "uid": "n1-1"}, "children": []},
                                ],
                            },
                            {
                                "data": {"text": "异常登录", "uid": "n2"},
                                "children": [
                                    {"data": {"text": "密码错误", "uid": "n2-1"}, "children": []},
                                ],
                            },
                        ],
                    },
                    "layout": "logicalStructure",
                },
                "locked_by": None,
                "locked_at": None,
            }
        }

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        auth = request.headers.get("authorization")

        if path == "/health":
            if self.fail_health:
                return httpx.Response(503, json={"detail": "down"})
            return httpx.Response(200, json={"status": "ok"})

        if path == "/api/v1/common/auth/login" and request.method == "POST":
            return httpx.Response(
                200, json={"access_token": FAKE_TOKEN, "token_type": "bearer", "expires_in": 2592000}
            )

        if auth != f"Bearer {FAKE_TOKEN}":
            return httpx.Response(401, json={"detail": {"code": "unauthorized", "message": "未登录或 token 无效"}})

        if path == "/api/v1/common/auth/me":
            return httpx.Response(
                200,
                json={
                    "username": "mcp-bot",
                    "role_name": "viewer",
                    "perms": ["xmind:view", "task:view", "wiki:view"],
                    "full_name": "MCP Bot",
                    "email": None,
                    "department": None,
                    "job_scope": None,
                    "is_active": True,
                    "last_login_at": None,
                    "created_at": "2026-11-01T08:00:00",
                },
            )

        if path == "/api/v1/case/folders/tree":
            return httpx.Response(200, json={"items": [{"id": "f1", "name": "核心功能", "parent_id": None, "depth": 0, "owner": "tester", "created_at": "2026-11-01T08:00:00"}]})

        if path == "/api/v1/case/maps" and request.method == "GET":
            items = [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "owner": m["owner"],
                    "folder_id": m["folder_id"],
                    "current_version": m["current_version"],
                    "created_at": m["created_at"],
                    "last_modified_at": m["last_modified_at"],
                }
                for m in self.maps.values()
            ]
            return httpx.Response(200, json={"items": items})

        if path.startswith("/api/v1/case/maps/") and request.method == "GET" and "/" not in path[len("/api/v1/case/maps/"):]:
            map_id = path.rsplit("/", 1)[-1]
            m = self.maps.get(map_id)
            if m is None:
                return httpx.Response(404, json={"detail": {"code": "map_not_found", "message": "导图不存在"}})
            return httpx.Response(200, json=m)

        if path == "/api/v1/task/lists":
            return httpx.Response(200, json={"items": [{"id": "l1", "name": "工作", "owner": "mcp-bot", "members": [], "is_shared": False, "color": "#fff", "icon": None, "group": None, "board_groups": [], "kind": "task", "sort_order": 0, "is_archived": False, "created_at": "2026-11-01T08:00:00"}]})

        if path == "/api/v1/task/tags":
            return httpx.Response(200, json={"items": [{"id": "t1", "name": "回归", "color": None, "parent_id": None, "sort_order": 0, "created_at": "2026-11-01T08:00:00"}]})

        if path == "/api/v1/task/filters":
            return httpx.Response(200, json={"items": []})

        if path == "/api/v1/task/tasks" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "task1",
                            "title": "写登录用例",
                            "note": None,
                            "list_id": "l1",
                            "group": None,
                            "parent_id": None,
                            "owner": "mcp-bot",
                            "assignee": None,
                            "status": "todo",
                            "completed_at": None,
                            "priority": 3,
                            "tags": ["回归"],
                            "due_at": "2026-11-10T18:00:00",
                            "all_day": False,
                            "start_at": None,
                            "duration_minutes": None,
                            "reminders": [],
                            "persistent_reminder": False,
                            "attachments": [],
                            "recurrence": None,
                            "next_due": None,
                            "occurrences_completed": 0,
                            "case_map_id": "map1",
                            "case_node_id": "n1",
                            "is_pinned": False,
                            "is_note": False,
                            "sort_order": 0,
                            "subtask_total": 1,
                            "subtask_done": 0,
                            "created_at": "2026-11-01T08:00:00",
                            "updated_at": "2026-11-01T08:00:00",
                        }
                    ]
                },
            )

        if path == "/api/v1/task/tasks/task1" and request.method == "GET":
            task = json.loads(self.handler_task1())
            return httpx.Response(200, json=task)

        if path == "/api/v1/wiki/vaults" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "v1",
                            "name": "团队知识库",
                            "description": "",
                            "owner": "mcp-bot",
                            "remote_url": None,
                            "default_branch": "main",
                            "auto_commit_interval": 300,
                            "status": "ready",
                            "status_message": "",
                            "created_at": "2026-11-01T08:00:00",
                            "updated_at": "2026-11-01T08:00:00",
                        }
                    ]
                },
            )

        if path == "/api/v1/wiki/vaults/v1/pages/tree":
            return httpx.Response(
                200,
                json=[
                    {"type": "folder", "name": "docs", "path": "docs", "children": [
                        {"type": "page", "name": "index.md", "path": "docs/index.md", "children": []}
                    ]}
                ],
            )

        if path == "/api/v1/wiki/vaults/v1/pages/content":
            page_path = request.url.params.get("path")
            if request.method == "GET":
                if page_path in self.pages:
                    return httpx.Response(
                        200,
                        json={
                            "path": page_path,
                            "content": self.pages[page_path],
                            "locked_by": self.page_locks.get(page_path),
                        },
                    )
                return httpx.Response(404, json={"detail": {"code": "page_not_found", "message": "页面不存在"}})
            if request.method == "PUT":
                body = json.loads(request.content)
                if self.page_conflict or self.put_conflict:
                    return httpx.Response(423, json={"detail": {"code": "page_locked", "message": "页面被他人锁定"}})
                self.pages[body["path"]] = body["content"]
                return httpx.Response(200, json={"path": body["path"], "title": body["path"].rsplit("/", 1)[-1]})

        if path == "/api/v1/wiki/vaults/v1/pages" and request.method == "POST":
            body = json.loads(request.content)
            if body["path"] in self.pages:
                return httpx.Response(409, json={"detail": {"code": "page_exists", "message": "页面已存在"}})
            self.pages[body["path"]] = body["content"]
            return httpx.Response(200, json={"path": body["path"], "title": body["path"].rsplit("/", 1)[-1]})

        if path == "/api/v1/wiki/vaults/v1/pages/lock":
            page_path = request.url.params.get("path")
            if request.method == "POST":
                body = json.loads(request.content)
                page_path = body["path"]
                if self.page_conflict:
                    return httpx.Response(423, json={"detail": {"code": "page_locked", "message": "页面被他人锁定"}})
                self.page_locks[page_path] = body.get("holder") or "mcp-bot"
                return httpx.Response(200, json={"message": "锁定成功"})
            if request.method == "DELETE":
                self.page_locks.pop(page_path, None)
                return httpx.Response(200, json={"message": "已释放"})

        if path == "/api/v1/wiki/vaults/v1/pages/commit" and request.method == "POST":
            body = json.loads(request.content) if request.content else {}
            return httpx.Response(
                200,
                json={
                    "committed": True,
                    "commit": "abc1234",
                    "message": body.get("message") or "auto: snapshot",
                    "files": list(self.pages),
                    "date": "2026-11-09T08:00:00",
                },
            )

        if path == "/api/v1/wiki/vaults/v1/history" and request.method == "GET":
            page_path = request.url.params.get("path")
            return httpx.Response(
                200,
                json=[
                    {"commit": "abc1234", "author": "mcp-bot", "date": "2026-11-09T08:00:00", "message": f"update {page_path}"},
                    {"commit": "def5678", "author": "tester", "date": "2026-11-08T08:00:00", "message": "init"},
                ],
            )

        if path == "/api/v1/wiki/vaults/v1/history/diff" and request.method == "GET":
            return httpx.Response(200, json={"diff": "--- a/x.md\n+++ b/x.md\n@@ -1 +1 @@\n-旧\n+新", "truncated": False})

        if path == "/api/v1/wiki/vaults/v1/history/revert" and request.method == "POST":
            body = json.loads(request.content)
            self.pages[body["path"]] = f"# 回滚到 {body['commit']}"
            return httpx.Response(200, json={"message": "已回滚"})

        if path == "/api/v1/wiki/vaults/v1" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "v1",
                    "name": "团队知识库",
                    "status": "ready",
                    "remote_url": "git@example.com:team/wiki.git",
                    "default_branch": "main",
                    "changes": ["docs/index.md"],
                    "doc_count": len(self.pages),
                    "rebuild": {"running": False, "progress": 100},
                },
            )

        if path == "/api/v1/wiki/vaults/v1/pull" and request.method == "POST":
            return httpx.Response(200, json={"message": "pull 完成", "rebuild": {"running": False}})

        if path == "/api/v1/wiki/vaults/v1/push" and request.method == "POST":
            return httpx.Response(200, json={"message": "push 完成"})

        if path == "/api/v1/wiki/vaults/v1/rebuild-index" and request.method == "POST":
            if self.rebuild_running:
                return httpx.Response(409, json={"detail": {"code": "wiki_rebuild_running", "message": "索引重建中，请稍后查询进度"}})
            self.rebuild_running = True
            return httpx.Response(200, json={"message": "重建任务已启动", "status": "running"})

        if path == "/api/v1/wiki/vaults/v1/explore/search":
            return httpx.Response(200, json=[{"path": "docs/index.md", "title": "首页", "snippet": "你好", "field": "content"}])

        # ---- case write (P1) ----
        if path.startswith("/api/v1/case/maps/"):
            parts = path[len("/api/v1/case/maps/"):].split("/")
            map_id = parts[0]
            m = self.maps.get(map_id)
            sub = parts[1] if len(parts) > 1 else ""

            if sub == "lock" and request.method == "POST":
                if self.lock_conflict:
                    return httpx.Response(423, json={"detail": {"code": "map_locked", "message": "导图被他人锁定"}})
                if m:
                    m["locked_by"] = "mcp-bot"
                return httpx.Response(200, json={"message": "锁定成功"})
            if sub == "lock" and request.method == "DELETE":
                if m:
                    m["locked_by"] = None
                return httpx.Response(200, json={"message": "已释放"})
            if sub == "snapshot" and request.method == "POST":
                if m is None:
                    return httpx.Response(404, json={"detail": {"code": "map_not_found", "message": "导图不存在"}})
                body = json.loads(request.content)
                if self.cas_conflict:
                    return httpx.Response(409, json={"detail": {"code": "version_conflict", "message": "版本已变化"}})
                m["latest_root"] = body["root"]
                m["current_version"] = m.get("current_version", 1) + 1
                return httpx.Response(200, json={"map_id": map_id, "version_no": m["current_version"], "changelog": body.get("changelog", "")})
            if sub == "versions" and request.method == "GET":
                return httpx.Response(200, json={"items": [{"id": "v1", "map_id": map_id, "version_no": 2, "changelog": "上一版", "operator_id": "tester", "created_at": "2026-11-05T08:00:00"}], "total": 1})
            if sub == "rollback" and request.method == "POST":
                if m:
                    m["current_version"] = m.get("current_version", 1) + 1
                return httpx.Response(200, json={"map_id": map_id, "version_no": m["current_version"] if m else 1, "changelog": "回滚"})
            if not sub and request.method == "PATCH":
                if m is None:
                    return httpx.Response(404, json={"detail": {"code": "map_not_found", "message": "导图不存在"}})
                body = json.loads(request.content)
                if "temp_content" in body:
                    m["temp_content"] = body["temp_content"]
                if "title" in body:
                    m["title"] = body["title"]
                return httpx.Response(200, json={"message": "更新中"})

        if path == "/api/v1/case/maps" and request.method == "POST":
            body = json.loads(request.content)
            new_id = "map-new"
            self.maps[new_id] = {
                "id": new_id,
                "title": body["title"],
                "owner": "mcp-bot",
                "folder_id": body.get("folder_id"),
                "current_version": 1,
                "created_at": "2026-11-09T08:00:00",
                "last_modified_at": "2026-11-09T08:00:00",
                "temp_content": None,
                "latest_root": body.get("root"),
                "locked_by": None,
                "locked_at": None,
            }
            return httpx.Response(200, json={"id": new_id, "title": body["title"], "owner": "mcp-bot", "folder_id": body.get("folder_id"), "current_version": 1, "created_at": "2026-11-09T08:00:00", "last_modified_at": "2026-11-09T08:00:00"})

        # ---- task write (P1) ----
        if path == "/api/v1/task/tasks" and request.method == "POST":
            body = json.loads(request.content)
            task = {
                "id": "task-new",
                "title": body["title"],
                "note": body.get("note"),
                "list_id": body.get("list_id"),
                "group": None,
                "parent_id": body.get("parent_id"),
                "owner": "mcp-bot",
                "assignee": None,
                "status": "todo",
                "completed_at": None,
                "priority": body.get("priority", 0),
                "tags": body.get("tags", []),
                "due_at": body.get("due_at"),
                "all_day": False,
                "start_at": None,
                "duration_minutes": None,
                "reminders": [],
                "persistent_reminder": False,
                "attachments": [],
                "recurrence": None,
                "next_due": None,
                "occurrences_completed": 0,
                "case_map_id": None,
                "case_node_id": None,
                "is_pinned": False,
                "is_note": False,
                "sort_order": 0,
                "subtask_total": 0,
                "subtask_done": 0,
                "created_at": "2026-11-09T08:00:00",
                "updated_at": "2026-11-09T08:00:00",
            }
            return httpx.Response(200, json=task)

        if path.startswith("/api/v1/task/tasks/"):
            rest = path[len("/api/v1/task/tasks/"):]
            rest_parts = rest.split("/")
            task_id = rest_parts[0]
            sub = "/".join(rest_parts[1:])

            if sub == "" and request.method == "PATCH":
                body = json.loads(request.content)
                task = json.loads(self.handler_task1())
                task.update({k: v for k, v in body.items()})
                task["id"] = task_id
                return httpx.Response(200, json=task)
            if sub == "move" and request.method == "PATCH":
                body = json.loads(request.content)
                task = json.loads(self.handler_task1())
                task["list_id"] = body.get("list_id")
                return httpx.Response(200, json=task)
            if sub == "complete" and request.method == "POST":
                body = json.loads(request.content)
                task = json.loads(self.handler_task1())
                task["status"] = "done" if body.get("done") else "todo"
                task["id"] = task_id
                return httpx.Response(200, json=task)
            if sub == "skip" and request.method == "POST":
                task = json.loads(self.handler_task1())
                task["status"] = "skipped"
                return httpx.Response(200, json=task)
            if sub == "restore" and request.method == "POST":
                task = json.loads(self.handler_task1())
                task["status"] = "todo"
                return httpx.Response(200, json=task)
            if sub == "" and request.method == "DELETE":
                return httpx.Response(200, json={"message": "已删除"})
            if sub == "purge" and request.method == "DELETE":
                return httpx.Response(200, json={"message": "已清除"})

        if path == "/api/v1/task/tasks/batch" and request.method == "POST":
            body = json.loads(request.content)
            return httpx.Response(200, json={"succeeded": len(body.get("ids", [])), "failed": 0})

        # ---- analytics / focus / habits (P1) ----
        if path == "/api/v1/task/views/summary":
            return httpx.Response(200, json={"overdue": 2, "today_todo": 5, "completed_total": 42, "by_list": [{"list_id": "l1", "name": "工作", "todo": 3}]})

        if path == "/api/v1/task/summary/preview" and request.method == "POST":
            return httpx.Response(200, json={"markdown": "# 本周摘要\n\n- 写登录用例 !高\n", "total": 3, "groups": [{"name": "待办", "count": 2}]})

        if path == "/api/v1/task/focus" and request.method == "GET":
            return httpx.Response(200, json={"items": []})

        if path == "/api/v1/task/focus/stats":
            return httpx.Response(200, json={"total_seconds": 7500, "sessions": 5})

        if path == "/api/v1/task/focus/stats/detail":
            kind = request.url.params.get("kind", "breakdown")
            if kind not in {"trend", "hours", "heatmap", "timeline", "breakdown"}:
                return httpx.Response(400, json={"detail": {"code": "invalid_kind", "message": "kind 仅支持 trend/hours/heatmap/timeline/breakdown"}})
            return httpx.Response(200, json={"kind": kind, "rows": [{"key": "写登录用例", "seconds": 3600}]})

        if path == "/api/v1/task/habits" and request.method == "GET":
            return httpx.Response(200, json={"items": [{"id": "h1", "name": "晨跑", "today_checked": True, "today_skipped": False, "today_count": 1, "streak": 7, "week_bitmap": [True] * 7}, {"id": "h2", "name": "阅读", "today_checked": False, "today_skipped": False, "today_count": 0, "streak": 2, "week_bitmap": [True, False]}]})

        if path == "/api/v1/task/habits/week":
            return httpx.Response(200, json={"days": [{"date": "2026-11-03", "checked": 1, "total": 2}]})

        if path.startswith("/api/v1/task/habits/") and path.endswith("/stats"):
            return httpx.Response(200, json={"best_streak": 12, "total_days": 45})

        # ---- collab / focus / habits write (P2) ----
        if path == "/api/v1/task/tasks/task1/comments":
            if request.method == "GET":
                items = self.comments.get("task1", [])
                return httpx.Response(200, json={"items": items})
            if request.method == "POST":
                body = json.loads(request.content)
                comment = {"id": f"c{len(self.comments.get('task1', [])) + 1}", "content": body["content"], "author": "mcp-bot"}
                self.comments.setdefault("task1", []).append(comment)
                return httpx.Response(200, json=comment)

        if path == "/api/v1/task/views/calendar" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "task1", "title": "写登录用例", "due_at": "2026-11-10T18:00:00", "status": "todo", "list_id": "l1"}
                    ]
                },
            )

        if path == "/api/v1/task/views/pending-reminders" and request.method == "GET":
            return httpx.Response(
                200,
                json={"items": [{"task_id": "task1", "title": "写登录用例", "due_at": "2026-11-10T18:00:00", "priority": 3, "persistent": False, "remind_ats": ["2026-11-10T17:30:00"]}]},
            )

        if path == "/api/v1/task/tasks/task1/reminders/ack" and request.method == "POST":
            return httpx.Response(200, json={"ok": True})

        if path == "/api/v1/task/share/lists/l1/members":
            if request.method == "GET":
                return httpx.Response(200, json={"items": self.members["l1"]})
            if request.method == "POST":
                body = json.loads(request.content)
                self.members["l1"].append({"username": body["username"], "role": body.get("role", "viewer")})
                return httpx.Response(200, json={"items": self.members["l1"]})

        if path == "/api/v1/task/focus" and request.method == "POST":
            body = json.loads(request.content)
            sid = f"s{len(self.focus_sessions) + 1}"
            self.focus_sessions[sid] = {
                "id": sid,
                "status": "running",
                "task_id": body.get("task_id"),
                "planned_minutes": body.get("planned_minutes", 25),
                "actual_seconds": 0,
            }
            return httpx.Response(200, json=self.focus_sessions[sid])

        if path.startswith("/api/v1/task/focus/s") and request.method == "POST":
            rest = path[len("/api/v1/task/focus/"):]
            sid, _, action = rest.partition("/")
            session = self.focus_sessions.get(sid)
            if session is None:
                return httpx.Response(404, json={"detail": {"code": "session_not_found", "message": "会话不存在"}})
            if action == "pause":
                session["status"] = "paused"
            elif action == "resume":
                session["status"] = "running"
            elif action == "finish":
                session["status"] = "finished"
            elif action == "abandon":
                session["status"] = "abandoned"
            else:
                return httpx.Response(404, json={"detail": {"code": "not_found", "message": f"no stub for {path}"}})
            return httpx.Response(200, json=session)

        if path.startswith("/api/v1/task/habits/"):
            rest = path[len("/api/v1/task/habits/"):]
            hid, _, action = rest.partition("/")
            if action == "checkin" and request.method == "POST":
                return httpx.Response(200, json={"ok": True, "date": "2026-11-09", "count": 1})
            if action == "checkin" and request.method == "DELETE":
                return httpx.Response(200, json={"ok": True})
            if action == "skip" and request.method == "POST":
                return httpx.Response(200, json={"ok": True, "date": "2026-11-09", "skipped": True})

        # ---- admin domain (P3) ----
        if path == "/api/v1/common/auth/users" and request.method == "GET":
            items = list(self.users.values())
            q = request.url.params.get("q")
            if q:
                items = [u for u in items if q.lower() in u["username"].lower() or q.lower() in (u["full_name"] or "").lower()]
            return httpx.Response(200, json=items)

        if path == "/api/v1/common/auth/users" and request.method == "POST":
            body = json.loads(request.content)
            if body["username"] in self.users:
                return httpx.Response(400, json={"detail": {"code": "user_exists", "message": "用户已存在"}})
            user = {
                "username": body["username"],
                "role_name": body.get("role_name", "viewer"),
                "perms": [],
                "full_name": body.get("full_name"),
                "email": body.get("email"),
                "department": body.get("department"),
                "job_scope": body.get("job_scope"),
                "is_active": body.get("is_active", True),
                "last_login_at": None,
                "created_at": "2026-11-09T08:00:00",
            }
            self.users[user["username"]] = user
            return httpx.Response(200, json=user)

        if path == "/api/v1/common/auth/users/batch-permissions" and request.method == "POST":
            body = json.loads(request.content)
            updated = []
            for username in body["usernames"]:
                if username in self.users:
                    self.users[username]["role_name"] = body["role_name"]
                    updated.append(username)
            return httpx.Response(200, json={"updated": updated})

        if path.startswith("/api/v1/common/auth/users/"):
            rest = path[len("/api/v1/common/auth/users/"):]
            username, _, sub = rest.partition("/")
            if username not in self.users:
                return httpx.Response(404, json={"detail": {"code": "user_not_found", "message": "用户不存在"}})
            user = self.users[username]
            if sub == "permissions" and request.method == "PATCH":
                body = json.loads(request.content)
                user["role_name"] = body["role_name"]
                return httpx.Response(200, json=user)
            if sub == "active" and request.method == "PATCH":
                body = json.loads(request.content)
                user["is_active"] = body["is_active"]
                return httpx.Response(200, json=user)
            if sub == "job-scope" and request.method == "PATCH":
                body = json.loads(request.content)
                user["job_scope"] = body["job_scope"]
                return httpx.Response(200, json=user)
            if sub == "" and request.method == "DELETE":
                del self.users[username]
                return httpx.Response(200, json={"message": "已删除"})

        if path == "/api/v1/common/auth/roles" and request.method == "GET":
            return httpx.Response(200, json=[{k: v for k, v in r.items() if k != "is_builtin"} for r in self.roles.values()])

        if path == "/api/v1/common/auth/roles" and request.method == "POST":
            body = json.loads(request.content)
            if body["name"] in self.roles:
                return httpx.Response(400, json={"detail": {"code": "role_exists", "message": "角色已存在"}})
            self.roles[body["name"]] = {"name": body["name"], "permissions": body.get("permissions", []), "description": body.get("description"), "is_builtin": False}
            return httpx.Response(200, json=self.roles[body["name"]])

        if path.startswith("/api/v1/common/auth/roles/"):
            name = path[len("/api/v1/common/auth/roles/"):]
            role = self.roles.get(name)
            if role is None:
                return httpx.Response(404, json={"detail": {"code": "role_not_found", "message": "角色不存在"}})
            if request.method == "PATCH":
                if role["is_builtin"]:
                    return httpx.Response(403, json={"detail": {"code": "forbidden", "message": "内置角色不可编辑"}})
                body = json.loads(request.content)
                role["permissions"] = body.get("permissions", [])
                role["description"] = body.get("description")
                return httpx.Response(200, json={k: v for k, v in role.items() if k != "is_builtin"})
            if request.method == "DELETE":
                if role["is_builtin"]:
                    return httpx.Response(403, json={"detail": {"code": "forbidden", "message": "内置角色不可删除"}})
                if any(u["role_name"] == name for u in self.users.values()):
                    return httpx.Response(400, json={"detail": {"code": "role_in_use", "message": "仍有用户引用该角色"}})
                del self.roles[name]
                return httpx.Response(200, json={"message": "已删除"})

        if path == "/api/v1/common/platform/permissions" and request.method == "GET":
            return httpx.Response(200, json={"items": self.permission_keys})

        if path == "/api/v1/common/platform/permissions" and request.method == "POST":
            body = json.loads(request.content)
            if any(p["key"] == body["key"] for p in self.permission_keys):
                return httpx.Response(400, json={"detail": {"code": "permission_exists", "message": "权限 key 已存在"}})
            self.permission_keys.append({"key": body["key"], "app_id": body.get("app_id"), "builtin": body.get("builtin", False)})
            return httpx.Response(200, json={"item": body})

        if path.startswith("/api/v1/common/platform/permissions/") and request.method == "DELETE":
            key = path[len("/api/v1/common/platform/permissions/"):]
            item = next((p for p in self.permission_keys if p["key"] == key), None)
            if item is None:
                return httpx.Response(404, json={"detail": {"code": "permission_not_found", "message": "权限 key 不存在"}})
            if item["builtin"]:
                return httpx.Response(403, json={"detail": {"code": "forbidden", "message": "内置权限 key 不可删除"}})
            self.permission_keys = [p for p in self.permission_keys if p["key"] != key]
            return httpx.Response(200, json={"message": "已删除"})

        return httpx.Response(404, json={"detail": {"code": "not_found", "message": f"no stub for {path}"}})

    @staticmethod
    def handler_task1() -> str:
        return json.dumps(
            {
                "id": "task1",
                "title": "写登录用例",
                "note": None,
                "list_id": "l1",
                "group": None,
                "parent_id": None,
                "owner": "mcp-bot",
                "assignee": None,
                "status": "todo",
                "completed_at": None,
                "priority": 3,
                "tags": ["回归"],
                "due_at": "2026-11-10T18:00:00",
                "all_day": False,
                "start_at": None,
                "duration_minutes": None,
                "reminders": [],
                "persistent_reminder": False,
                "attachments": [],
                "recurrence": None,
                "next_due": None,
                "occurrences_completed": 0,
                "case_map_id": "map1",
                "case_node_id": "n1",
                "is_pinned": False,
                "is_note": False,
                "sort_order": 0,
                "subtask_total": 1,
                "subtask_done": 0,
                "created_at": "2026-11-01T08:00:00",
                "updated_at": "2026-11-01T08:00:00",
                "subtasks": [],
                "case_map_title": "登录模块",
                "case_node_text": "正常登录",
            },
            ensure_ascii=False,
        )


@pytest.fixture
def fake_backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def mock_transport(fake_backend) -> httpx.MockTransport:
    return httpx.MockTransport(fake_backend.handler)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def build_ctx(mock_transport, settings, monkeypatch, tmp_path):
    """Factory: build a fresh AppContext + MCPServer with the mock transport."""

    def _build(**setting_overrides):
        from studiosystem_mcp.client.http import StudioClient
        from studiosystem_mcp.context import AppContext
        from studiosystem_mcp.policy.audit import AuditLogger
        from studiosystem_mcp.policy.guard import ToolGuard

        s = make_settings(**setting_overrides)
        client = StudioClient(s, transport=mock_transport)
        audit = AuditLogger(str(tmp_path / "audit.jsonl"))
        return AppContext(settings=s, client=client, guard=ToolGuard(s), audit=audit)

    return _build
