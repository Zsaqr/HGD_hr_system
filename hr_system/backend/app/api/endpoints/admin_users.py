from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.endpoints.auth import require_login
from app.models.user import User

# نفس فكرة bcrypt/passlib اللي عندك في المشروع
# غالبًا عندك util جاهز للهاش. لو موجود هنستعمله.
try:
    from app.core.security import hash_password  # type: ignore
except Exception:
    hash_password = None  # هنfallback لو مش موجود

import bcrypt

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_current_user(db: AsyncSession, user_id: int) -> User | None:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


def _hash_pw(pw: str) -> str:
    if hash_password:
        return hash_password(pw)
    # fallback bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw.encode("utf-8"), salt).decode("utf-8")


@router.get("")
async def users_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        me = await get_current_user(db, user_id)
        if not (me and getattr(me, "is_admin", False)):
            return RedirectResponse("/?error=forbidden", status_code=302)


        users = (await db.execute(select(User).order_by(User.id.asc()))).scalars().all()

        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users},
        )


@router.post("/new")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    is_admin: str = Form("0"),
):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    username = (username or "").strip()
    password = (password or "").strip()
    flag_admin = (is_admin == "1")

    if not username or not password:
        return RedirectResponse("/users?error=missing", status_code=302)

    # مهم: bcrypt بيرفض أكتر من 72 bytes
    if len(password.encode("utf-8")) > 72:
        return RedirectResponse("/users?error=password_too_long", status_code=302)

    async for db in get_db():
        db: AsyncSession
        me = await get_current_user(db, user_id)
        if not (me and getattr(me, "is_admin", False)):
            return RedirectResponse("/?error=forbidden", status_code=302)


        exists = (await db.execute(select(User.id).where(User.username == username))).scalar_one_or_none()
        if exists:
            return RedirectResponse("/users?error=username_exists", status_code=302)

        u = User(
            username=username,
            password_hash=_hash_pw(password),
            is_admin=flag_admin,
        )
        db.add(u)
        await db.commit()

        return RedirectResponse("/users?success=1", status_code=302)
