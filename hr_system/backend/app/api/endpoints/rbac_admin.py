from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.endpoints.auth import require_login
from app.models.user import User
from app.core.rbac import user_has_permission

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_current_user(db: AsyncSession, user_id: int) -> User | None:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


@router.get("")
async def rbac_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    uid = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        me = await get_current_user(db, uid)
        if not me:
            return RedirectResponse("/login", status_code=302)

        # Admin فقط (بما إن UI حساسة)
        if not getattr(me, "is_admin", False):
            return RedirectResponse("/?error=forbidden", status_code=302)


        # جلب users/roles
        users = (await db.execute(select(User).order_by(User.id.asc()))).scalars().all()

        # roles table (بدون موديل؟ هنقرأها كـ SQL مباشرة)
        roles_rows = (await db.execute(select_text("select id, name from roles order by name asc"))).all()
        roles = [{"id": r[0], "name": r[1]} for r in roles_rows]

        # user_roles mapping
        ur_rows = (await db.execute(select_text("select user_id, role_id from user_roles"))).all()
        user_roles_map: dict[int, list[int]] = {}
        for u_id, r_id in ur_rows:
            user_roles_map.setdefault(int(u_id), []).append(int(r_id))

        # role_permissions mapping (عرض فقط)
        rp_rows = (await db.execute(select_text("""
            select rp.role_id, p.code
            from role_permissions rp
            join permissions p on p.id = rp.permission_id
            order by rp.role_id, p.code
        """))).all()
        role_perms: dict[int, list[str]] = {}
        for role_id, code in rp_rows:
            role_perms.setdefault(int(role_id), []).append(str(code))

        return templates.TemplateResponse(
            "rbac_admin.html",
            {
                "request": request,
                "users": users,
                "roles": roles,
                "user_roles_map": user_roles_map,
                "role_perms": role_perms,
            },
        )


@router.post("/assign")
async def assign_roles(
    request: Request,
    user_id: int = Form(...),
    role_ids: str = Form(""),
):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    uid = request.session.get("user_id")

    # role_ids جاية كـ string: "1,2,3"
    new_role_ids: list[int] = []
    if role_ids.strip():
        for part in role_ids.split(","):
            part = part.strip()
            if part.isdigit():
                new_role_ids.append(int(part))

    async for db in get_db():
        db: AsyncSession
        me = await get_current_user(db, uid)
        if not me or not getattr(me, "is_admin", False):
            return RedirectResponse("/?error=forbidden", status_code=302)


        # تأكد user موجود
        target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not target:
            return RedirectResponse("/rbac?error=user_not_found", status_code=302)

        # امسح roles القديمة للمستخدم
        await db.execute(select_text("delete from user_roles where user_id = :uid").bindparams(uid=user_id))

        # أضف roles الجديدة
        for rid in new_role_ids:
            await db.execute(
                select_text("insert into user_roles(user_id, role_id) values (:u, :r)")
                .bindparams(u=user_id, r=rid)
            )

        await db.commit()
        return RedirectResponse("/rbac?success=1", status_code=302)


# --- helper: SQL text without needing models ---
from sqlalchemy import text as select_text
