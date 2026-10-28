from typing import Any, Dict


def sanitize_node(root: Dict[str, Any]) -> Dict[str, Any]:
    """兜底处理节点 text，确保为字符串。"""
    def walk(node: Dict[str, Any]):
        data = node.get("data", {})
        if not isinstance(data.get("text"), str):
            data["text"] = str(data.get("text", ""))
        node["data"] = data
        for child in node.get("children", []):
            walk(child)
        return node

    return walk(root)
