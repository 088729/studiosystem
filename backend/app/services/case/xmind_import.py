import asyncio
import json
import os
import zipfile
from io import BytesIO
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from app.models.case.case_map import CaseMap
from app.models.case.case_version import CaseVersion
from app.services.case.asset_service import upload_asset
from app.services.case.map_service import create_map


def _parse_xmind_json(content: bytes) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data
    except Exception:
        return None


def _parse_xmind_xml(content: bytes) -> Optional[Dict[str, Any]]:
    try:
        root = ET.fromstring(content)
        ns = {"xmap": "urn:xmind:xmap:xmlns:content:2.0"}
        topic = root.find(".//topic", ns)
        if topic is None:
            topic = root.find(".//{urn:xmind:xmap:xmlns:content:2.0}topic")
        if topic is None:
            return None

        def parse_topic(element: ET.Element) -> Dict[str, Any]:
            title_el = element.find("title", ns)
            if title_el is None:
                title_el = element.find("{urn:xmind:xmap:xmlns:content:2.0}title")
            text = title_el.text if title_el is not None else "未命名"

            node = {
                "data": {
                    "text": text or "未命名",
                    "expand": True,
                },
                "children": [],
            }

            children_el = element.find("children", ns)
            if children_el is None:
                children_el = element.find("{urn:xmind:xmap:xmlns:content:2.0}children")
            if children_el is not None:
                topics_el = children_el.find("topics", ns)
                if topics_el is None:
                    topics_el = children_el.find("{urn:xmind:xmap:xmlns:content:2.0}topics")
                if topics_el is not None:
                    topics = topics_el.findall("topic", ns)
                    for child in topics:
                        node["children"].append(parse_topic(child))
            return node

        return parse_topic(topic)
    except Exception:
        return None


def _topic_to_node(topic: Dict[str, Any]) -> Dict[str, Any]:
    title = ""
    if isinstance(topic.get("title"), str):
        title = topic["title"]
    elif isinstance(topic.get("title"), dict):
        title = topic["title"].get("text", "")

    node = {
        "data": {
            "text": title or "未命名",
            "expand": True,
        },
        "children": [],
    }

    image = topic.get("image")
    if image:
        node["data"]["image"] = image.get("src", "")

    children = topic.get("children", {}).get("attached", [])
    for child in children:
        node["children"].append(_topic_to_node(child))
    return node


def _extract_root(content_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    root_topic = content_json.get("rootTopic") or content_json.get("topic")
    if root_topic is None:
        return None
    return _topic_to_node(root_topic)


def _build_full_data(root_node: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "root": root_node,
        "layout": "logicalStructure",
        "theme": {"template": "default", "config": {}},
        "view": {"transform": {"scale": 1, "x": 0, "y": 0}},
    }


def _find_attachment_files(zf: zipfile.ZipFile) -> Dict[str, bytes]:
    """收集 zip 中 attachments 目录下的文件。"""
    files = {}
    for name in zf.namelist():
        if name.startswith("attachments/") and not name.endswith("/"):
            files[os.path.basename(name)] = zf.read(name)
    return files


async def _upload_one(map_id: str, filename: str, file_bytes: bytes):
    return await upload_asset(
        map_id=map_id,
        node_id="xmind_import",
        filename=filename,
        file_bytes=file_bytes,
    )


async def _upload_attachments(
    attachments: Dict[str, bytes],
    map_id: str,
) -> Dict[str, str]:
    """并发上传附件到资源平台，返回文件名 -> URL 映射。"""
    url_map = {}
    tasks = []
    filenames = []
    for filename, file_bytes in attachments.items():
        tasks.append(_upload_one(map_id, filename, file_bytes))
        filenames.append(filename)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for filename, result in zip(filenames, results):
        if isinstance(result, Exception):
            continue
        url_map[filename] = result.url
    return url_map


def _replace_image_urls(node: Dict[str, Any], url_map: Dict[str, str]) -> None:
    data = node.get("data", {})
    image_src = data.get("image", "")
    if image_src:
        # xmind 图片 src 格式通常为 xap:attachments/{filename}
        filename = os.path.basename(image_src)
        if filename in url_map:
            data["image"] = url_map[filename]
    for child in node.get("children", []):
        _replace_image_urls(child, url_map)


async def import_xmind_file(
    content: bytes,
    filename: str,
    folder_id: Optional[str],
    owner: str,
) -> CaseMap:
    try:
        zf = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile:
        raise ValueError("文件不是有效的 .xmind zip 压缩包")

    root_node: Optional[Dict[str, Any]] = None

    if "content.json" in zf.namelist():
        data = zf.read("content.json")
        content_json = _parse_xmind_json(data)
        if content_json:
            root_node = _extract_root(content_json)

    if root_node is None and "content.xml" in zf.namelist():
        data = zf.read("content.xml")
        root_node = _parse_xmind_xml(data)

    if root_node is None:
        raise ValueError("无法解析 xmind 内容")

    title = root_node["data"]["text"]
    full_data = _build_full_data(root_node)

    map_obj = await create_map(
        title=title,
        folder_id=folder_id,
        root=full_data,
        owner=owner,
    )

    # 提取并上传图片附件
    attachments = _find_attachment_files(zf)
    if attachments:
        url_map = await _upload_attachments(attachments, str(map_obj.id))
        _replace_image_urls(full_data["root"], url_map)
        # 更新初始版本的 root
        version = await CaseVersion.find_one(
            CaseVersion.map_id == str(map_obj.id),
            CaseVersion.version_no == 1,
        )
        if version is not None:
            version.root = full_data
            version.changelog = "xmind 导入"
            await version.save()

    return map_obj
