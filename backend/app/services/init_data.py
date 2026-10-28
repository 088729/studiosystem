import logging
import os

from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger(__name__)


async def init_admin_user() -> None:
    existing = await User.find_one(User.username == "admin")
    if existing is None:
        password = os.environ.get("ADMIN_INITIAL_PASSWORD", "admin123")
        if password == "admin123":
            logger.warning(
                "未设置 ADMIN_INITIAL_PASSWORD，使用默认 admin 密码: admin123 "
                "（本地开发可用，生产环境请务必设置 ADMIN_INITIAL_PASSWORD）"
            )
        user = User(
            username="admin",
            hashed_password=get_password_hash(password),
            role_name="admin",
            full_name="Administrator",
            is_active=True,
        )
        await user.insert()
