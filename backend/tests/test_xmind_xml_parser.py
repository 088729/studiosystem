"""XMind XML 解析单元测试（无需数据库）."""

import pytest

from app.services.case.xmind_import import _parse_xmind_xml


@pytest.mark.asyncio
async def test_parse_xmind_xml_nested_topics():
    """XML 解析应只取直接子 topic，避免递归重复."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<xmind version="2.0">
  <sheet>
    <topic>
      <title>根节点</title>
      <children>
        <topics type="attached">
          <topic>
            <title>子节点1</title>
            <children>
              <topics type="attached">
                <topic>
                  <title>孙节点</title>
                </topic>
              </topics>
            </children>
          </topic>
          <topic>
            <title>子节点2</title>
          </topic>
        </topics>
      </children>
    </topic>
  </sheet>
</xmind>
"""
    root = _parse_xmind_xml(xml.encode("utf-8"))
    assert root is not None
    assert root["data"]["text"] == "根节点"
    # 根节点应只有 2 个直接子节点
    assert len(root["children"]) == 2
    assert root["children"][0]["data"]["text"] == "子节点1"
    assert root["children"][1]["data"]["text"] == "子节点2"
    # 孙节点应挂在子节点1下，且只出现一次
    assert len(root["children"][0]["children"]) == 1
    assert root["children"][0]["children"][0]["data"]["text"] == "孙节点"
