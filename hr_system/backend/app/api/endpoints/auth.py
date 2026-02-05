from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.security import verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_login(request: Request):
    return request.session.get("user_id")

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "hide_nav": True, "error": None})

@router.post("/login")
async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    async for db in get_db():
        db: AsyncSession
        q = await db.execute(select(User).where(User.username == username))
        user = q.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "اسم المستخدم أو كلمة المرور غير صحيحة"},
                status_code=401,
            )

        request.session["user_id"] = user.id
        return RedirectResponse(url="/", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
