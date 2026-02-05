from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.department import Department
from app.api.endpoints.auth import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("")
async def list_departments(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        res = await db.execute(select(Department).order_by(Department.name))
        items = res.scalars().all()
        return templates.TemplateResponse("departments.html", {"request": request, "items": items})

@router.get("/new")
async def new_department_form(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("department_form.html", {"request": request, "item": None})

@router.post("/new")
async def create_department(request: Request, name: str = Form(...)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        dep = Department(name=name.strip())
        db.add(dep)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return RedirectResponse("/departments", status_code=302)

@router.post("/{dep_id}/delete")
async def delete_department(request: Request, dep_id: int):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        await db.execute(delete(Department).where(Department.id == dep_id))
        await db.commit()
        return RedirectResponse("/departments", status_code=302)
