from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def user_has_permission(db: AsyncSession, user_id: int, perm_code: str) -> bool:
    sql = text(
        """
        SELECT 1
        FROM user_roles ur
        JOIN role_permissions rp ON rp.role_id = ur.role_id
        JOIN permissions p ON p.id = rp.permission_id
        WHERE ur.user_id = :user_id
          AND p.code = :perm_code
        LIMIT 1
        """
    )
    res = await db.execute(sql, {"user_id": user_id, "perm_code": perm_code})
    return res.first() is not None
