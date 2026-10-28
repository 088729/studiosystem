from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.exceptions import not_found
from app.models.case.case_map import CaseMap
from app.models.case.case_version import CaseVersion
from app.services.case.map_service import get_map_or_404
from app.utils.validators import sanitize_node


async def get_version_or_404(map_id: str, version_no: int) -> CaseVersion:
    version = await CaseVersion.find_one(
        CaseVersion.map_id == map_id,
        CaseVersion.version_no == version_no,
    )
    if version is None:
        raise not_found("version_not_found", "版本不存在")
    return version


async def list_versions(map_id: str, offset: int = 0, limit: int = 20) -> tuple[List[CaseVersion], int]:
    await get_map_or_404(map_id)
    total = await CaseVersion.find(CaseVersion.map_id == map_id).count()
    versions = (
        await CaseVersion.find(CaseVersion.map_id == map_id)
        .sort(-CaseVersion.version_no)
        .skip(offset)
        .limit(limit)
        .to_list()
    )
    return versions, total


async def create_snapshot(
    map_id: str,
    root: Dict[str, Any],
    changelog: str,
    overwrite: bool,
    operator: str,
) -> CaseVersion:
    map_obj = await get_map_or_404(map_id)

    root["root"] = sanitize_node(root["root"])

    if overwrite:
        version = await get_version_or_404(map_id, map_obj.current_version)
        version.root = root
        version.changelog = changelog
        version.operator_id = operator
        version.created_at = datetime.now(timezone.utc)
        await version.save()
    else:
        map_obj.current_version += 1
        version = CaseVersion(
            map_id=map_id,
            version_no=map_obj.current_version,
            root=root,
            changelog=changelog,
            operator_id=operator,
        )
        await version.insert()
        await map_obj.save()

    map_obj.temp_content = None
    await map_obj.save()
    return version


async def rollback_version(map_id: str, version_no: int, operator: str) -> CaseVersion:
    map_obj = await get_map_or_404(map_id)
    target = await get_version_or_404(map_id, version_no)

    map_obj.current_version += 1
    new_version = CaseVersion(
        map_id=map_id,
        version_no=map_obj.current_version,
        root=target.root,
        changelog=f"回滚至 v{version_no}",
        operator_id=operator,
    )
    await new_version.insert()

    map_obj.temp_content = None
    await map_obj.save()
    return new_version
