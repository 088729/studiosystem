"""Normalized errors: backend `{"detail": {"code","message"}}` → readable StudioError."""

from __future__ import annotations

from typing import Any


class StudioError(Exception):
    """Error normalized from the Studio backend (or local validation).

    `hint` suggests a concrete next action for the AI client.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        hint: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.hint = hint

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": False, "code": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        if self.status is not None:
            out["status"] = self.status
        return out

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        suffix = f"（{self.hint}）" if self.hint else ""
        return f"[{self.code}] {self.message}{suffix}"


_STATUS_HINTS: dict[int, str] = {
    401: "凭据失效：检查 STUDIO_MCP_AUTH_MODE 与凭据配置，或确认服务账号未被停用",
    403: "当前账号缺少所需权限键，请在后台为 mcp-bot 补充 extra_permissions 后重试（权限即时生效，无需重启）",
    404: "目标不存在或 id 有误，可先用对应的 list 工具确认 id",
    409: "目标已被他人修改，请重新读取后再操作",
    423: "目标正被他人锁定，请稍后重试",
    422: "请求参数不符合后端 schema，请对照工具说明调整字段",
}


def error_from_response(status_code: int, payload: Any) -> StudioError:
    """Build a StudioError from an HTTP error response body."""
    code = f"http_{status_code}"
    message = f"后端返回 {status_code}"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            code = str(detail.get("code") or code)
            message = str(detail.get("message") or message)
        elif isinstance(detail, str):
            message = detail
    hint = _STATUS_HINTS.get(status_code)
    return StudioError(code=code, message=message, status=status_code, hint=hint)
