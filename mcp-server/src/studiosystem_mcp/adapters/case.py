"""Case (mind map) adapter: tree ↔ text outline, node addressing, trimming.

The backend stores simple-mind-map shaped data:

    {"root": {"data": {"text", "uid", "expand", ...}, "children": [...]},
     "layout": ..., "theme": ..., "view": ...}

AI clients should never see raw tree JSON; they get a compact text outline and
(in P1) node-level patches that MCP applies internally via read-modify-write.
"""

from __future__ import annotations

import re

MAX_OUTLINE_CHARS = 20000

_rich_tag_re = re.compile(r"<[^>]+>")


def node_text(node: dict) -> str:
    """Extract plain text from a node's `data.text` (may be rich-text HTML)."""
    data = node.get("data") or {}
    text = data.get("text")
    if not isinstance(text, str):
        text = str(text or "")
    text = _rich_tag_re.sub("", text)
    return " ".join(text.split())


def node_uid(node: dict) -> str:
    data = node.get("data") or {}
    return str(data.get("uid") or data.get("id") or "")


def iter_nodes(root: dict):
    """Yield (node, depth) depth-first."""
    stack: list[tuple[dict, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        yield node, depth
        children = node.get("children") or []
        for child in reversed(children):
            stack.append((child, depth + 1))


def count_nodes(root: dict) -> int:
    return sum(1 for _ in iter_nodes(root))


def find_node(root: dict, uid: str) -> dict | None:
    for node, _ in iter_nodes(root):
        if node_uid(node) == uid:
            return node
    return None


def outline(root_node: dict, *, max_chars: int = MAX_OUTLINE_CHARS) -> str:
    """Render the tree as an indented text outline with stable node ids.

    Format (one node per line):
        [uid] 节点文本            (root, depth 0)
          ├─ [uid] 子节点文本
          └─ [uid] 子节点文本

    Stops with a truncation marker if the output exceeds `max_chars`.
    """
    lines: list[str] = []
    total = 0

    def emit(line: str) -> bool:
        nonlocal total
        total += len(line) + 1
        if total > max_chars:
            return False
        lines.append(line)
        return True

    def walk(node: dict, depth: int) -> bool:
        uid = node_uid(node) or "?"
        text = node_text(node) or "(空)"
        prefix = "  " * depth
        if not emit(f"{prefix}[{uid}] {text}"):  # noqa: E231 - readable format
            return False
        children = node.get("children") or []
        for child in children:
            if not walk(child, depth + 1):
                return False
        return True

    walk(root_node, 0)
    if total > max_chars:
        lines.append("…（大纲过长已截断，请按节点缩小范围）")
    return "\n".join(lines)


def trim_items(items: list[dict], limit: int) -> tuple[list[dict], bool]:
    """Trim a list result; returns (kept, has_more)."""
    if len(items) <= limit:
        return items, False
    return items[:limit], True


# ---------- node-level patching (P1 case_edit_map) ----------

class PatchError(ValueError):
    """Invalid node patch — surfaced to the model as an isError result."""


def _deep_copy_tree(node: dict) -> dict:
    import json as _json

    return _json.loads(_json.dumps(node))


def _find_parent(root: dict, uid: str) -> dict | None:
    """Return the direct parent node of `uid`, or None if uid==root/not found."""
    for node, _ in iter_nodes(root):
        for child in node.get("children") or []:
            if node_uid(child) == uid:
                return node
    return None


def apply_patches(root_node: dict, patches: list[dict]) -> tuple[dict, dict]:
    """Apply node-level patches to a tree copy.

    Patch ops:
      add    {"op":"add",    "parent": "<uid>", "text": str, "index": int?}
      update {"op":"update", "uid": "<uid>",   "text": str}
      delete {"op":"delete", "uid": "<uid>"}
      move   {"op":"move",   "uid": "<uid>",   "parent": "<uid>", "index": int?}

    The root node (uid == tree root) cannot be deleted or moved. Returns
    (new_root, summary) where summary is a structured change list for the
    confirmation preview. Raises PatchError on any invalid reference.
    """
    tree = _deep_copy_tree(root_node)
    root_uid = node_uid(tree)
    summary: dict[str, list] = {"added": [], "updated": [], "deleted": [], "moved": []}

    def node_of(uid: str, *, what: str) -> dict:
        node = find_node(tree, uid)
        if node is None:
            raise PatchError(f"{what}: 找不到节点 uid={uid}")
        return node

    for i, patch in enumerate(patches):
        op = patch.get("op")
        if op == "add":
            parent_uid = str(patch.get("parent") or root_uid)
            parent = node_of(parent_uid, what=f"patches[{i}] add")
            text = str(patch.get("text") or "").strip()
            if not text:
                raise PatchError(f"patches[{i}] add: text 不能为空")
            import uuid

            child = {
                "data": {"text": text, "uid": f"mcp-{uuid.uuid4().hex[:12]}", "expand": True},
                "children": [],
            }
            children = parent.setdefault("children", [])
            index = patch.get("index")
            if index is None or index >= len(children):
                children.append(child)
            else:
                children.insert(max(0, int(index)), child)
            summary["added"].append({"uid": child["data"]["uid"], "text": text, "parent": parent_uid})
        elif op == "update":
            uid = str(patch.get("uid") or "")
            if uid == root_uid:
                raise PatchError(f"patches[{i}] update: 不能修改根节点文本（请改导图标题）")
            node = node_of(uid, what=f"patches[{i}] update")
            old = node_text(node)
            text = str(patch.get("text") or "").strip()
            if not text:
                raise PatchError(f"patches[{i}] update: text 不能为空")
            node.setdefault("data", {})["text"] = text
            summary["updated"].append({"uid": uid, "from": old, "to": text})
        elif op == "delete":
            uid = str(patch.get("uid") or "")
            if uid == root_uid:
                raise PatchError(f"patches[{i}] delete: 不能删除根节点")
            parent = _find_parent(tree, uid)
            if parent is None:
                raise PatchError(f"patches[{i}] delete: 找不到节点 uid={uid}")
            children = parent.get("children") or []
            victim = next(c for c in children if node_uid(c) == uid)
            summary["deleted"].append(
                {"uid": uid, "text": node_text(victim), "subtree_nodes": count_nodes(victim)}
            )
            parent["children"] = [c for c in children if node_uid(c) != uid]
        elif op == "move":
            uid = str(patch.get("uid") or "")
            new_parent_uid = str(patch.get("parent") or root_uid)
            if uid == root_uid:
                raise PatchError(f"patches[{i}] move: 不能移动根节点")
            node = node_of(uid, what=f"patches[{i}] move")
            new_parent = node_of(new_parent_uid, what=f"patches[{i}] move")
            # guard against moving into own descendant
            if find_node(node, new_parent_uid) is not None and new_parent_uid != uid:
                raise PatchError(f"patches[{i}] move: 不能把节点移动到自己的子树里")
            old_parent = _find_parent(tree, uid)
            assert old_parent is not None
            old_parent["children"] = [c for c in old_parent.get("children", []) if node_uid(c) != uid]
            children = new_parent.setdefault("children", [])
            index = patch.get("index")
            if index is None or index >= len(children):
                children.append(node)
            else:
                children.insert(max(0, int(index)), node)
            summary["moved"].append(
                {"uid": uid, "text": node_text(node), "from": node_uid(old_parent), "to": new_parent_uid}
            )
        else:
            raise PatchError(f"patches[{i}]: 未知 op={op!r}（可用 add/update/delete/move）")

    return tree, summary


def outline_to_tree(title: str, outline: str) -> dict:
    """Build a tree from an indented text outline (2 spaces per level, `- ` bullet optional).

        登录模块           ← 根（用 title 参数，或第一行）
          正常登录
            输入账号密码
          异常登录
    """
    lines = [ln for ln in outline.splitlines() if ln.strip()]
    if not lines:
        return {"data": {"text": title, "uid": "root", "expand": True}, "children": []}

    def indent_of(line: str) -> int:
        stripped = line.lstrip(" ")
        return (len(line) - len(stripped)) // 2

    def text_of(line: str) -> str:
        t = line.strip()
        return t[2:].strip() if t.startswith("- ") else t

    import uuid

    root = {"data": {"text": title or text_of(lines[0]), "uid": "root", "expand": True}, "children": []}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for line in lines:
        is_title_dup = (
            node_uid(root) == "root"
            and text_of(line) == root["data"]["text"]
            and indent_of(line) == 0
        )
        if is_title_dup:
            continue  # first line duplicates the title
        depth = indent_of(line)
        node = {
            "data": {"text": text_of(line), "uid": f"mcp-{uuid.uuid4().hex[:12]}", "expand": True},
            "children": [],
        }
        while stack and stack[-1][0] >= depth:
            stack.pop()
        stack[-1][1].setdefault("children", []).append(node)
        stack.append((depth, node))
    return root
