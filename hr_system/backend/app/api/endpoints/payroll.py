# app/api/endpoints/payroll.py

from datetime import date, datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.endpoints.auth import require_login
from app.core.rbac import user_has_permission
from app.core.audit import log_event  # ✅ AUDIT

from app.models.user import User
from app.models.employee import Employee
from app.models.allowance import Allowance
from app.models.deduction import Deduction
from app.models.payroll_run import PayrollRun
from app.models.payroll_item import PayrollItem

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_current_user(db: AsyncSession, user_id: int) -> User | None:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


async def is_admin_or(db: AsyncSession, user: User | None, perm: str) -> bool:
    if not user:
        return False
    if getattr(user, "is_admin", False):
        return True
    return await user_has_permission(db, user.id, perm)


@router.get("")
async def payroll_page(request: Request, employee_id: int | None = None):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        current_user = await get_current_user(db, user_id)

        can_view = await is_admin_or(db, current_user, "payroll.view")
        can_run = await is_admin_or(db, current_user, "payroll.run")
        can_update_salary = await is_admin_or(db, current_user, "payroll.salary.update")

        # ✅ SECURITY: block payroll page if no view permission
        if not can_view:
            return RedirectResponse("/?error=forbidden", status_code=302)


        emp_rows = (await db.execute(select(Employee).order_by(Employee.full_name.asc()))).scalars().all()
        if not emp_rows:
            return templates.TemplateResponse(
                "payroll.html",
                {
                    "request": request,
                    "employees": [],
                    "employee": None,
                    "allowances": [],
                    "deductions": [],
                    "runs": [],
                    "can_view": can_view,
                    "can_run": can_run,
                    "can_update_salary": can_update_salary,
                },
            )

        if employee_id is None:
            employee_id = emp_rows[0].id

        employee = next((e for e in emp_rows if e.id == employee_id), None)
        if not employee:
            return RedirectResponse("/payroll?error=employee_not_found", status_code=302)

        allowances = (
            await db.execute(
                select(Allowance)
                .where(Allowance.employee_id == employee_id)
                .order_by(desc(Allowance.created_at))
            )
        ).scalars().all()

        deductions = (
            await db.execute(
                select(Deduction)
                .where(Deduction.employee_id == employee_id)
                .order_by(desc(Deduction.created_at))
            )
        ).scalars().all()

        runs = (
            await db.execute(
                select(PayrollRun).order_by(desc(PayrollRun.created_at)).limit(10)
            )
        ).scalars().all()

        return templates.TemplateResponse(
            "payroll.html",
            {
                "request": request,
                "employees": emp_rows,
                "employee": employee,
                "allowances": allowances,
                "deductions": deductions,
                "runs": runs,
                "can_view": can_view,
                "can_run": can_run,
                "can_update_salary": can_update_salary,
            },
        )


@router.post("/employee/{employee_id}/salary")
async def update_salary(request: Request, employee_id: int, base_salary: float = Form(...)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    actor_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        actor = await get_current_user(db, actor_id)

        # ✅ permission gate
        allowed = await is_admin_or(db, actor, "payroll.salary.update")
        if not allowed:
            return RedirectResponse("/payroll?error=forbidden", status_code=302)

        emp = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
        if not emp:
            return RedirectResponse("/payroll?error=employee_not_found", status_code=302)

        emp.base_salary = base_salary
        await db.commit()

        # ✅ AUDIT
        await log_event(
            db,
            actor_user_id=actor_id,
            action="payroll.salary.update",
            entity="employee",
            entity_id=employee_id,
            meta={"base_salary": float(base_salary)},
        )
        await db.commit()

        return RedirectResponse(f"/payroll?employee_id={employee_id}", status_code=302)


@router.post("/employee/{employee_id}/allowances/new")
async def add_allowance(request: Request, employee_id: int, name: str = Form(...), amount: float = Form(...)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    actor_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        actor = await get_current_user(db, actor_id)

        # ✅ permission gate
        allowed = await is_admin_or(db, actor, "payroll.run")
        if not allowed:
            return RedirectResponse("/payroll?error=forbidden", status_code=302)

        emp = (await db.execute(select(Employee.id).where(Employee.id == employee_id))).scalar_one_or_none()
        if not emp:
            return RedirectResponse("/payroll?error=employee_not_found", status_code=302)

        a = Allowance(
            employee_id=employee_id,
            name=name.strip(),
            amount=amount,
            active=True,
            created_at=datetime.utcnow(),
        )
        db.add(a)
        await db.commit()
        await db.refresh(a)

        # ✅ AUDIT
        await log_event(
            db,
            actor_user_id=actor_id,
            action="payroll.allowance.create",
            entity="allowance",
            entity_id=a.id,
            meta={"employee_id": employee_id, "name": a.name, "amount": float(amount)},
        )
        await db.commit()

        return RedirectResponse(f"/payroll?employee_id={employee_id}", status_code=302)


@router.post("/employee/{employee_id}/deductions/new")
async def add_deduction(request: Request, employee_id: int, name: str = Form(...), amount: float = Form(...)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    actor_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        actor = await get_current_user(db, actor_id)

        # ✅ permission gate
        allowed = await is_admin_or(db, actor, "payroll.run")
        if not allowed:
            return RedirectResponse("/payroll?error=forbidden", status_code=302)

        emp = (await db.execute(select(Employee.id).where(Employee.id == employee_id))).scalar_one_or_none()
        if not emp:
            return RedirectResponse("/payroll?error=employee_not_found", status_code=302)

        d = Deduction(
            employee_id=employee_id,
            name=name.strip(),
            amount=amount,
            active=True,
            created_at=datetime.utcnow(),
        )
        db.add(d)
        await db.commit()
        await db.refresh(d)

        # ✅ AUDIT
        await log_event(
            db,
            actor_user_id=actor_id,
            action="payroll.deduction.create",
            entity="deduction",
            entity_id=d.id,
            meta={"employee_id": employee_id, "name": d.name, "amount": float(amount)},
        )
        await db.commit()

        return RedirectResponse(f"/payroll?employee_id={employee_id}", status_code=302)


@router.post("/run")
async def run_payroll(
    request: Request,
    period_start: str = Form(...),
    period_end: str = Form(...),
    notes: str = Form(""),
):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    try:
        ps = date.fromisoformat(period_start)
        pe = date.fromisoformat(period_end)
    except Exception:
        return RedirectResponse("/payroll?error=bad_date", status_code=302)

    if pe < ps:
        return RedirectResponse("/payroll?error=range", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        current_user = await get_current_user(db, user_id)
        if not current_user:
            return RedirectResponse("/payroll?error=forbidden", status_code=302)

        # ✅ permission gate
        allowed = await is_admin_or(db, current_user, "payroll.run")
        if not allowed:
            return RedirectResponse("/payroll?error=forbidden", status_code=302)

        run = PayrollRun(
            period_start=ps,
            period_end=pe,
            status="draft",
            notes=(notes or "").strip() or None,
            created_by=current_user.id,
            created_at=datetime.utcnow(),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        employees = (await db.execute(select(Employee))).scalars().all()
        for emp in employees:
            allow_total = (
                await db.execute(
                    select(func.coalesce(func.sum(Allowance.amount), 0)).where(
                        Allowance.employee_id == emp.id,
                        Allowance.active.is_(True),
                    )
                )
            ).scalar_one()

            ded_total = (
                await db.execute(
                    select(func.coalesce(func.sum(Deduction.amount), 0)).where(
                        Deduction.employee_id == emp.id,
                        Deduction.active.is_(True),
                    )
                )
            ).scalar_one()

            base = emp.base_salary or 0
            net = base + allow_total - ded_total

            db.add(
                PayrollItem(
                    run_id=run.id,
                    employee_id=emp.id,
                    base_salary=base,
                    allowances_total=allow_total,
                    deductions_total=ded_total,
                    net_pay=net,
                    generated_at=datetime.utcnow(),
                )
            )

        run.status = "posted"
        await db.commit()

        # ✅ AUDIT
        await log_event(
            db,
            actor_user_id=current_user.id,
            action="payroll.run",
            entity="payroll_run",
            entity_id=run.id,
            meta={"period_start": str(ps), "period_end": str(pe), "status": run.status},
        )
        await db.commit()

        return RedirectResponse("/payroll?success=1", status_code=302)
