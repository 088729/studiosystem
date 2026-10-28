from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_perm
from app.models.user import User
from app.services.task import share_service

router = APIRouter()


class MemberIn(BaseModel):
    username: str
    role: str = "viewer"  # viewer | editor


class MemberRoleIn(BaseModel):
    role: str


class TransferIn(BaseModel):
    to: str


@router.get("/users")
async def list_share_users(current_user: User = Depends(require_perm("task:view"))):
    """成员选择数据源：全部活跃用户。"""
    users = await share_service.list_active_users()
    return {
        "items": [
            {"username": u.username, "full_name": u.full_name} for u in users
        ]
    }


@router.get("/lists/{list_id}/members")
async def list_members(
    list_id: str,
    current_user: User = Depends(require_perm("task:view")),
):
    task_list = await share_service.get_accessible_list_or_404(list_id, current_user.username)
    return {"items": task_list.members or []}


@router.post("/lists/{list_id}/members")
async def add_member(
    list_id: str,
    data: MemberIn,
    current_user: User = Depends(require_perm("task:share")),
):
    task_list = await share_service.add_member(
        list_id, data.username, current_user.username, data.role
    )
    return {"items": task_list.members or []}


@router.patch("/lists/{list_id}/members/{username}")
async def set_member_role(
    list_id: str,
    username: str,
    data: MemberRoleIn,
    current_user: User = Depends(require_perm("task:share")),
):
    """修改成员角色（仅清单所有者）。"""
    task_list = await share_service.set_member_role(
        list_id, username, data.role, current_user.username
    )
    return {"items": task_list.members or []}


# 注意：/members/me 必须先于 /members/{username} 注册，否则 "me" 会被当 username 匹配
@router.delete("/lists/{list_id}/members/me")
async def leave_list(
    list_id: str,
    current_user: User = Depends(require_perm("task:view")),
):
    """成员自助退出共享。"""
    return await share_service.leave_list(list_id, current_user.username)


@router.delete("/lists/{list_id}/members/{username}")
async def remove_member(
    list_id: str,
    username: str,
    current_user: User = Depends(require_perm("task:share")),
):
    task_list = await share_service.remove_member(list_id, username, current_user.username)
    return {"items": task_list.members or []}


@router.post("/lists/{list_id}/transfer")
async def transfer_owner(
    list_id: str,
    data: TransferIn,
    current_user: User = Depends(require_perm("task:manage")),
):
    """转移所有权给某成员；原 owner 降为 editor。"""
    task_list = await share_service.transfer_owner(list_id, data.to, current_user.username)
    return {"items": task_list.members or []}
