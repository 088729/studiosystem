"""P1 case write tests: patch engine, confirm flow, CAS, lock conflict, draft."""

import json

import pytest
from conftest import make_settings

from studiosystem_mcp.adapters.case import PatchError, apply_patches, outline_to_tree
from studiosystem_mcp.server import build_server


@pytest.fixture
def _tree():
    return {
        "data": {"text": "根", "uid": "root"},
        "children": [
            {"data": {"text": "A", "uid": "a"}, "children": [{"data": {"text": "A1", "uid": "a1"}, "children": []}]},
            {"data": {"text": "B", "uid": "b"}, "children": []},
        ],
    }


class TestApplyPatches:
    def test_add_update_delete_move(self, _tree):
        new, summary = apply_patches(
            _tree,
            [
                {"op": "add", "parent": "b", "text": "B1"},
                {"op": "update", "uid": "a", "text": "A-改"},
                {"op": "move", "uid": "a1", "parent": "b"},
                {"op": "delete", "uid": "a"},
            ],
        )
        assert len(summary["added"]) == 1 and summary["added"][0]["text"] == "B1"
        assert summary["updated"][0]["from"] == "A" and summary["updated"][0]["to"] == "A-改"
        assert summary["moved"][0]["uid"] == "a1"
        assert summary["deleted"][0]["uid"] == "a"
        # a deleted with subtree; a1 moved under b
        assert new["children"][0]["data"]["uid"] == "b"
        children_of_b = [c["data"]["uid"] for c in new["children"][0]["children"]]
        assert "a1" in children_of_b
        # original tree untouched (deep copy)
        assert _tree["children"][0]["data"]["text"] == "A"

    def test_invalid_references(self, _tree):
        with pytest.raises(PatchError):
            apply_patches(_tree, [{"op": "update", "uid": "ghost", "text": "x"}])
        with pytest.raises(PatchError):
            apply_patches(_tree, [{"op": "add", "parent": "ghost", "text": "x"}])
        with pytest.raises(PatchError):
            apply_patches(_tree, [{"op": "delete", "uid": "root"}])
        with pytest.raises(PatchError):
            apply_patches(_tree, [{"op": "move", "uid": "a", "parent": "a1"}])  # into own subtree
        with pytest.raises(PatchError):
            apply_patches(_tree, [{"op": "frobnicate", "uid": "a"}])

    def test_outline_to_tree(self):
        root = outline_to_tree("登录模块", "登录模块\n  正常登录\n    输入账号密码\n  异常登录")
        assert root["data"]["text"] == "登录模块"
        assert [c["data"]["text"] for c in root["children"]] == ["正常登录", "异常登录"]
        assert root["children"][0]["children"][0]["data"]["text"] == "输入账号密码"


@pytest.fixture
async def mcp_ctx(mock_transport, tmp_path):
    mcp, ctx = build_server(
        make_settings(audit_file=str(tmp_path / "audit.jsonl")),
        transport=mock_transport,
    )
    yield mcp, ctx
    await ctx.aclose()


class TestCaseEditMap:
    async def test_requires_confirmation_first(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool(
            "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "正常登录(改)"}]}
        )
        payload = json.loads(result.content[0].text)
        assert payload["requires_confirmation"] is True
        assert payload["confirm_token"].startswith("cft_")
        assert payload["preview"]["changes"]["updated"][0]["to"] == "正常登录(改)"
        assert payload["preview"]["base_version"] == 3

    async def test_dry_run_no_token(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = await mcp.call_tool(
            "case_edit_map",
            {"map_id": "map1", "patches": [{"op": "add", "parent": "root", "text": "新分支"}], "dry_run": True},
        )
        payload = json.loads(result.content[0].text)
        assert payload["dry_run"] is True
        assert "confirm_token" not in payload

    async def test_execute_with_token_full_cycle(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (await mcp.call_tool(
                "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n2-1", "text": "密码错误(锁定账号)"}]}
            )).content[0].text
        )
        token = first["confirm_token"]
        second = json.loads(
            (await mcp.call_tool(
                "case_edit_map",
                {"map_id": "map1", "patches": [{"op": "update", "uid": "n2-1", "text": "X"}], "confirm_token": token},
            )).content[0].text
        )
        assert second["ok"] is True
        assert second["version_no"] == 4
        # full cycle happened: lock → get(CAS) → snapshot → unlock
        paths = [r.url.path for r in fake_backend.requests if "map1" in r.url.path]
        assert any(p.endswith("/lock") for p in paths)
        assert any(p.endswith("/snapshot") for p in paths)
        assert fake_backend.maps["map1"]["locked_by"] is None  # released

    async def test_token_single_use(self, mcp_ctx):
        mcp, _ = mcp_ctx
        first = json.loads(
            (await mcp.call_tool(
                "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "t1"}]}
            )).content[0].text
        )
        await mcp.call_tool(
            "case_edit_map",
            {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "t1"}], "confirm_token": first["confirm_token"]},
        )
        third = json.loads(
            (await mcp.call_tool(
                "case_edit_map",
                {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "t1"}], "confirm_token": first["confirm_token"]},
            )).content[0].text
        )
        assert third["ok"] is False and third["code"] == "confirm_token_invalid"

    async def test_confirm_mode_none_executes_directly(self, mock_transport):
        mcp, ctx = build_server(make_settings(confirm_mode="none"), transport=mock_transport)
        try:
            result = json.loads(
                (await mcp.call_tool(
                    "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "直接改"}]}
                )).content[0].text
            )
            assert result["ok"] is True and result["version_no"] == 4
        finally:
            await ctx.aclose()

    async def test_cas_conflict_aborts(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (await mcp.call_tool(
                "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "并发改"}]}
            )).content[0].text
        )
        fake_backend.cas_conflict = True
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "case_edit_map",
                {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "X"}], "confirm_token": first["confirm_token"]},
            )
        assert "version_conflict" in str(ei.value) or "409" in str(ei.value)
        fake_backend.cas_conflict = False

    async def test_lock_conflict_readable(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        first = json.loads(
            (await mcp.call_tool(
                "case_edit_map", {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "锁测试"}]}
            )).content[0].text
        )
        fake_backend.lock_conflict = True
        with pytest.raises(Exception) as ei:
            await mcp.call_tool(
                "case_edit_map",
                {"map_id": "map1", "patches": [{"op": "update", "uid": "n1", "text": "X"}], "confirm_token": first["confirm_token"]},
            )
        assert "锁定" in str(ei.value)
        fake_backend.lock_conflict = False


class TestCaseVersions:
    async def test_list(self, mcp_ctx):
        mcp, _ = mcp_ctx
        payload = json.loads((await mcp.call_tool("case_versions", {"map_id": "map1"})).content[0].text)
        assert payload["total"] == 1
        assert payload["versions"][0]["version_no"] == 2

    async def test_rollback_requires_allow_destructive(self, mock_transport):
        mcp, ctx = build_server(make_settings(), transport=mock_transport)
        try:
            tools = {t.name for t in await mcp.list_tools()}
            assert "case_versions" in tools  # 工具注册；rollback 子操作受 allow_destructive 控制
            with pytest.raises(Exception) as ei:
                await mcp.call_tool("case_versions", {"map_id": "map1", "action": "rollback", "version_no": 2})
            assert "ALLOW_DESTRUCTIVE" in str(ei.value)
        finally:
            await ctx.aclose()

        mcp2, ctx2 = build_server(make_settings(allow_destructive=True), transport=mock_transport)
        try:
            first = json.loads(
                (await mcp2.call_tool("case_versions", {"map_id": "map1", "action": "rollback", "version_no": 2})).content[0].text
            )
            assert first["requires_confirmation"] is True
            second = json.loads(
                (await mcp2.call_tool(
                    "case_versions",
                    {"map_id": "map1", "action": "rollback", "version_no": 2, "confirm_token": first["confirm_token"]},
                )).content[0].text
            )
            assert second["ok"] is True
        finally:
            await ctx2.aclose()

    async def test_save_draft(self, mcp_ctx, fake_backend):
        mcp, _ = mcp_ctx
        result = json.loads(
            (await mcp.call_tool(
                "case_save_draft", {"map_id": "map1", "patches": [{"op": "add", "parent": "root", "text": "草稿节点"}]}
            )).content[0].text
        )
        assert result["ok"] is True
        assert "异步" in result["note"]
        assert fake_backend.maps["map1"]["temp_content"]["root"]["children"][-1]["data"]["text"] == "草稿节点"

    async def test_create_map_with_outline(self, mcp_ctx):
        mcp, _ = mcp_ctx
        result = json.loads(
            (await mcp.call_tool("case_create_map", {"title": "支付模块", "outline": "支付模块\n  支付宝\n  微信"})).content[0].text
        )
        assert result["ok"] is True
        assert result["map"]["id"] == "map-new"
        assert result["node_count"] == 3
