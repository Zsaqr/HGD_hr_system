from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.models.attendance import Attendance

router = APIRouter(prefix="/attendance", tags=["Attendance"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def attendance_page(
    request: Request,
    employee_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    # get employees list for dropdown (id + name فقط)
    from app.models.employee import Employee

    employees_q = select(Employee.id, Employee.full_name).order_by(Employee.full_name.asc())
    employees_rows = (await db.execute(employees_q)).all()
    employees = [{"id": r[0], "full_name": r[1]} for r in employees_rows]

    # لو مفيش موظفين خالص
    if not employees:
        return templates.TemplateResponse(
            "attendance.html",
            {
                "request": request,
                "employee_id": None,
                "employees": [],
                "open_attendance": None,
                "history": [],
            },
        )

    # لو مفيش employee_id في query، اختار أول موظف
    if employee_id is None:
        employee_id = employees[0]["id"]

    # validate employee_id موجود فعلاً في القائمة
    if employee_id not in {e["id"] for e in employees}:
        return RedirectResponse(url="/attendance/?error=employee_not_found", status_code=303)

    open_q = (
        select(Attendance)
        .where(Attendance.employee_id == employee_id, Attendance.check_out.is_(None))
        .order_by(Attendance.check_in.desc())
        .limit(1)
    )
    open_row = (await db.execute(open_q)).scalars().first()

    history_q = (
        select(Attendance)
        .where(Attendance.employee_id == employee_id)
        .order_by(Attendance.check_in.desc())
        .limit(30)
    )
    history = (await db.execute(history_q)).scalars().all()

    return templates.TemplateResponse(
        "attendance.html",
        {
            "request": request,
            "employee_id": employee_id,
            "employees": employees,
            "open_attendance": open_row,
            "history": history,
        },
    )


@router.post("/check-in")
async def check_in(
    employee_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # validate employee exists
    from app.models.employee import Employee

    emp = (await db.execute(select(Employee.id).where(Employee.id == employee_id))).scalar_one_or_none()
    if not emp:
        return RedirectResponse(url="/attendance/?error=employee_not_found", status_code=303)

    row = Attendance(employee_id=employee_id, check_in=datetime.utcnow(), check_out=None)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return RedirectResponse(
            url=f"/attendance/?employee_id={employee_id}&error=open_exists",
            status_code=303,
        )

    return RedirectResponse(url=f"/attendance/?employee_id={employee_id}", status_code=303)


@router.post("/check-out")
async def check_out(
    employee_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # validate employee exists
    from app.models.employee import Employee

    emp = (await db.execute(select(Employee.id).where(Employee.id == employee_id))).scalar_one_or_none()
    if not emp:
        return RedirectResponse(url="/attendance/?error=employee_not_found", status_code=303)

    # اقفل "آخر open attendance" فقط
    open_q = (
        select(Attendance)
        .where(Attendance.employee_id == employee_id, Attendance.check_out.is_(None))
        .order_by(Attendance.check_in.desc())
        .limit(1)
    )
    open_row = (await db.execute(open_q)).scalars().first()

    if not open_row:
        return RedirectResponse(
            url=f"/attendance/?employee_id={employee_id}&error=no_open",
            status_code=303,
        )

    open_row.check_out = datetime.utcnow()
    await db.commit()

    return RedirectResponse(url=f"/attendance/?employee_id={employee_id}", status_code=303)
