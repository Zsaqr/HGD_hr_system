from datetime import date

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.employee import Employee
from app.models.department import Department
from app.api.endpoints.auth import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def list_employees(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession

        # مهم: نحمّل department مسبقًا عشان مانعملش lazy load داخل Jinja
        res = await db.execute(
            select(Employee)
            .options(selectinload(Employee.department))
            .order_by(Employee.full_name)
        )
        items = res.scalars().all()
        return templates.TemplateResponse(
            "employees.html",
            {"request": request, "items": items},
        )


@router.get("/new")
async def new_employee_form(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        deps = (await db.execute(select(Department).order_by(Department.name))).scalars().all()
        return templates.TemplateResponse(
            "employee_form.html",
            {"request": request, "deps": deps, "item": None},
        )


@router.post("/new")
async def create_employee(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    job_title: str = Form(""),
    hire_date: str = Form(""),
    department_id: str = Form(""),
):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    parsed_date = None
    if hire_date:
        try:
            y, m, d = hire_date.split("-")
            parsed_date = date(int(y), int(m), int(d))
        except Exception:
            parsed_date = None

    dep_id = int(department_id) if department_id.strip().isdigit() else None

    async for db in get_db():
        db: AsyncSession
        emp = Employee(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            job_title=job_title.strip(),
            hire_date=parsed_date,
            department_id=dep_id,
        )
        db.add(emp)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

        return RedirectResponse("/employees", status_code=302)


@router.post("/{emp_id}/delete")
async def delete_employee(request: Request, emp_id: int):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        await db.execute(delete(Employee).where(Employee.id == emp_id))
        await db.commit()
        return RedirectResponse("/employees", status_code=302)
