"""Adapter unit tests: outline rendering, quick-add parsing, path validation."""

from datetime import date

import pytest

from studiosystem_mcp.adapters import case as case_ad
from studiosystem_mcp.adapters import task as task_ad
from studiosystem_mcp.adapters import wiki as wiki_ad
from studiosystem_mcp.errors import StudioError


def _tree():
    return {
        "data": {"text": "登录模块", "uid": "root"},
        "children": [
            {
                "data": {"text": "正常登录", "uid": "n1"},
                "children": [{"data": {"text": "输入正确账号密码", "uid": "n1-1"}, "children": []}],
            },
            {"data": {"text": "异常<b>登录</b>", "uid": "n2"}, "children": []},
        ],
    }


class TestCaseAdapter:
    def test_outline_renders_uids_and_nesting(self):
        out = case_ad.outline(_tree())
        lines = out.splitlines()
        assert lines[0] == "[root] 登录模块"
        assert "  [n1] 正常登录" in lines
        assert "    [n1-1] 输入正确账号密码" in lines
        assert "[n2] 异常登录" in out  # rich-text tags stripped

    def test_outline_truncates(self):
        big = {"data": {"text": "x" * 100, "uid": "r"}, "children": [
            {"data": {"text": "y" * 100, "uid": f"c{i}"}, "children": []} for i in range(50)
        ]}
        out = case_ad.outline(big, max_chars=500)
        assert "截断" in out

    def test_find_and_count(self):
        tree = _tree()
        assert case_ad.count_nodes(tree) == 4
        assert case_ad.find_node(tree, "n1-1")["data"]["text"] == "输入正确账号密码"
        assert case_ad.find_node(tree, "nope") is None

    def test_trim_items(self):
        kept, more = case_ad.trim_items([1, 2, 3], 2)
        assert kept == [1, 2] and more
        kept, more = case_ad.trim_items([1], 2)
        assert kept == [1] and not more


class TestTaskAdapter:
    def test_parse_quick_add_full(self):
        fields = task_ad.parse_quick_add("写登录用例 @明天 !高 ~回归 #登录", today=date(2026, 11, 9))
        assert fields["title"] == "写登录用例"
        assert fields["due_at"] == "2026-11-10"
        assert fields["priority"] == 3
        assert fields["tags"] == ["回归"]
        assert fields["list_name"] == "登录"

    def test_parse_quick_add_defaults(self):
        fields = task_ad.parse_quick_add("买牛奶", today=date(2026, 11, 9))
        assert fields == {"tags": [], "title": "买牛奶"}

    def test_parse_quick_add_numeric_priority_and_iso_date(self):
        fields = task_ad.parse_quick_add(" review !2 @2026-12-01 ", today=date(2026, 11, 9))
        assert fields["priority"] == 2
        assert fields["due_at"] == "2026-12-01"
        assert fields["title"] == "review"

    def test_parse_quick_add_bad_date_raises(self):
        with pytest.raises(ValueError):
            task_ad.parse_quick_add("x @NotADate", today=date(2026, 11, 9))

    def test_parse_quick_add_title_required(self):
        with pytest.raises(ValueError):
            task_ad.parse_quick_add("#只有清单", today=date(2026, 11, 9))

    def test_format_task_line(self):
        line = task_ad.format_task_line(
            {"id": "t1", "title": "写用例", "status": "todo", "priority": 3, "due_at": "2026-11-10T18:00:00", "tags": ["回归"], "subtask_total": 2, "subtask_done": 1}
        )
        assert "[t1]" in line and "!高" in line and "截止 2026-11-10" in line and "~回归" in line and "1/2" in line


class TestWikiAdapter:
    @pytest.mark.parametrize(
        "bad",
        ["../etc/passwd.md", "a/../b.md", "/abs.md", "CON.md", "x/.git/y.md", "a\\b.md", "no_ext", "dir/.md", "a/.."],
    )
    def test_invalid_paths(self, bad):
        with pytest.raises(StudioError):
            wiki_ad.validate_rel_path(bad)

    def test_valid_path_normalized(self):
        assert wiki_ad.validate_rel_path("docs/./a.md") == "docs/a.md"

    def test_tree_render(self):
        nodes = [{"type": "folder", "name": "docs", "path": "docs", "children": [{"type": "page", "name": "a.md", "path": "docs/a.md", "children": []}]}]
        out = wiki_ad.render_tree(nodes)
        assert "docs" in out and "docs/a.md" in out

    def test_trim_page_content(self):
        content, truncated = wiki_ad.trim_page_content("x" * 100000)
        assert truncated and "省略" in content and len(content) < 60000
