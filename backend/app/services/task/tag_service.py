from typing import List, Optional

from bson import ObjectId

from app.core.exceptions import bad_request, not_found
from app.models.task.tag import Tag
from app.models.task.task import Task
from app.services.case.folder_service import is_valid_oid


async def get_tag_or_404(tag_id: str, owner: str) -> Tag:
    if not is_valid_oid(tag_id):
        raise not_found("tag_not_found", "标签不存在")
    tag = await Tag.get(ObjectId(tag_id))
    if tag is None or tag.owner != owner:
        raise not_found("tag_not_found", "标签不存在")
    return tag


async def list_tags(owner: str) -> List[Tag]:
    return await Tag.find(Tag.owner == owner).sort("sort_order").to_list()


async def _check_name_unique(name: str, owner: str, exclude_id: Optional[ObjectId] = None) -> None:
    query = Tag.find(Tag.owner == owner, Tag.name == name)
    if exclude_id is not None:
        query = Tag.find(Tag.owner == owner, Tag.name == name, Tag.id != exclude_id)
    if await query.count() > 0:
        raise bad_request("tag_name_conflict", "标签名已存在")


async def _check_parent(parent_id: Optional[str], owner: str, self_id: Optional[str] = None) -> None:
    """上级标签校验：存在、归属当前用户、本身是顶级标签（只允许一级层级）、非自身。"""
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise bad_request("tag_parent_invalid", "上级标签不能是自身")
    parent = await get_tag_or_404(parent_id, owner)
    if parent.parent_id is not None:
        raise bad_request("tag_parent_invalid", "上级标签必须是顶级标签（不支持二级以上嵌套）")


async def create_tag(
    name: str,
    color: Optional[str],
    owner: str,
    parent_id: Optional[str] = None,
) -> Tag:
    await _check_name_unique(name, owner)
    await _check_parent(parent_id, owner)
    last = (
        await Tag.find(Tag.owner == owner)
        .sort("-sort_order")
        .limit(1)
        .to_list()
    )
    sort_order = (last[0].sort_order + 1) if last else 0
    tag = Tag(name=name, owner=owner, color=color, parent_id=parent_id, sort_order=sort_order)
    await tag.insert()
    return tag


async def update_tag(tag_id: str, data: dict, owner: str) -> Tag:
    tag = await get_tag_or_404(tag_id, owner)
    old_name = tag.name
    new_name = data.get("name")
    if new_name is not None and new_name != old_name:
        await _check_name_unique(new_name, owner, exclude_id=tag.id)
    if "parent_id" in data:
        await _check_parent(data["parent_id"], owner, self_id=tag_id)
        # 自身有下级标签时不允许再挂到别人下面（保持一级层级）
        if data["parent_id"] is not None:
            children = await Tag.find(Tag.parent_id == tag_id).count()
            if children > 0:
                raise bad_request("tag_parent_invalid", "含有下级标签的标签不能设置上级")
    for key, value in data.items():
        setattr(tag, key, value)
    await tag.save()
    # 重命名级联改写所有任务（含子任务）的 tags 数组
    if new_name is not None and new_name != old_name:
        await rename_tag_cascade(old_name, new_name, owner)
    return tag


async def rename_tag_cascade(old_name: str, new_name: str, owner: str) -> None:
    """把 owner 所有任务 tags 数组里的 old_name 改写为 new_name。"""
    coll = Task.get_motor_collection()
    await coll.update_many(
        {"owner": owner, "tags": old_name},
        {"$set": {"tags.$[elem]": new_name}},
        array_filters=[{"elem": old_name}],
    )


async def delete_tag(tag_id: str, owner: str) -> None:
    tag = await get_tag_or_404(tag_id, owner)
    # 级联删除下级标签
    children = await Tag.find(Tag.parent_id == tag_id).to_list()
    names = [t.name for t in children] + [tag.name]
    for child in children:
        await child.delete()
    await tag.delete()
    # 从所有任务的 tags 数组移除这些标签名（不删任务）
    coll = Task.get_motor_collection()
    await coll.update_many(
        {"owner": owner, "tags": {"$in": names}},
        {"$pull": {"tags": {"$in": names}}},
    )
