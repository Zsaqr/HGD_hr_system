from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.api.router import router
from app.models.user import User
from app.core.security import hash_password

import app.models  # noqa: F401


# ✅ NEW: attendance router
from app.routers.attendance import router as attendance_router

templates = Jinja2Templates(directory="app/templates")

app = FastAPI(title="HR System MVP")
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)

from fastapi.responses import RedirectResponse

@app.get("/dashboard")
async def dashboard_alias():
    return RedirectResponse("/", status_code=302)


# ✅ NEW: include attendance router
app.include_router(attendance_router)

@app.on_event("startup")
async def startup():
    # MVP: create tables automatically. Later: Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin if not exists
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        admin = res.scalar_one_or_none()
        if not admin:
            db.add(
                User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    is_admin=True,
                )
            )
            await db.commit()

@app.get("/")
async def home(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})


