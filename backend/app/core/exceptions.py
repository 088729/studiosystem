from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status


def error_detail(
    code: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    detail: Dict[str, Any] = {"code": code, "message": message}
    if extra:
        detail.update(extra)
    return detail


def bad_request(code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error_detail(code, message, extra),
    )


def unauthorized(message: str = "未登录或 token 无效") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=error_detail("unauthorized", message),
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "无权限") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=error_detail("forbidden", message),
    )


def not_found(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(code, message),
    )


def conflict(code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error_detail(code, message, extra),
    )


def locked(code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail=error_detail(code, message, extra),
    )


def unprocessable(code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error_detail(code, message, extra),
    )


def bad_gateway(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=error_detail("bad_gateway", message),
    )
