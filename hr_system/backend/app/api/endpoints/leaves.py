# app/api/endpoints/leaves.py

from datetime import date, datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.endpoints.auth import require_login
from app.core.rbac import user_has_permission

from app.models.user import User
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_current_user(db: AsyncSession, user_id: int) -> User | None:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


@router.get("")
async def leaves_page(request: Request, employee_id: int | None = None):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        current_user = await get_current_user(db, user_id)

        can_approve = bool(current_user) and (
            getattr(current_user, "is_admin", False)
            or await user_has_permission(db, current_user.id, "leaves.approve")
        )

        employees = (await db.execute(select(Employee).order_by(Employee.full_name.asc()))).scalars().all()
        if not employees:
            return templates.TemplateResponse(
                "leaves.html",
                {
                    "request": request,
                    "employees": [],
                    "employee_id": None,
                    "items": [],
                    "can_approve": can_approve,
                },
            )

        if employee_id is None:
            employee_id = employees[0].id

        emp = next((e for e in employees if e.id == employee_id), None)
        if not emp:
            return RedirectResponse("/leaves?error=employee_not_found", status_code=302)

        items = (
            await db.execute(
                select(LeaveRequest)
                .where(LeaveRequest.employee_id == employee_id)
                .order_by(desc(LeaveRequest.created_at))
                .limit(50)
            )
        ).scalars().all()

        return templates.TemplateResponse(
            "leaves.html",
            {
                "request": request,
                "employees": employees,
                "employee_id": employee_id,
                "employee": emp,
                "items": items,
                "can_approve": can_approve,
            },
        )


@router.post("/new")
async def create_leave(
    request: Request,
    employee_id: int = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...),
    leave_type: str = Form("annual"),
    reason: str = Form(""),
):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    # parse dates
    try:
        fd = date.fromisoformat(from_date)
        td = date.fromisoformat(to_date)
    except Exception:
        return RedirectResponse(f"/leaves?employee_id={employee_id}&error=bad_date", status_code=302)

    if td < fd:
        return RedirectResponse(f"/leaves?employee_id={employee_id}&error=range", status_code=302)

    async for db in get_db():
        db: AsyncSession

        emp = (await db.execute(select(Employee.id).where(Employee.id == employee_id))).scalar_one_or_none()
        if not emp:
            return RedirectResponse("/leaves?error=employee_not_found", status_code=302)

        lr = LeaveRequest(
            employee_id=employee_id,
            from_date=fd,
            to_date=td,
            leave_type=(leave_type or "annual").strip() or "annual",
            reason=(reason or "").strip() or None,
            status="pending",
            approved_by=None,
            created_at=datetime.utcnow(),
            decided_at=None,
        )
        db.add(lr)
        await db.commit()

        return RedirectResponse(f"/leaves?employee_id={employee_id}&success=1", status_code=302)


@router.post("/{leave_id}/approve")
async def approve_leave(request: Request, leave_id: int):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        current_user = await get_current_user(db, user_id)
        if not current_user:
            return RedirectResponse("/leaves?error=forbidden", status_code=302)

        allowed = await user_has_permission(db, current_user.id, "leaves.approve")
        if not (getattr(current_user, "is_admin", False) or allowed):
            return RedirectResponse("/leaves?error=forbidden", status_code=302)

        lr = (await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))).scalar_one_or_none()
        if not lr:
            return RedirectResponse("/leaves?error=not_found", status_code=302)

        lr.status = "approved"
        lr.approved_by = current_user.id
        lr.decided_at = datetime.utcnow()
        await db.commit()

        return RedirectResponse(f"/leaves?employee_id={lr.employee_id}&success=1", status_code=302)


@router.post("/{leave_id}/reject")
async def reject_leave(request: Request, leave_id: int):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    user_id = request.session.get("user_id")

    async for db in get_db():
        db: AsyncSession
        current_user = await get_current_user(db, user_id)
        if not current_user:
            return RedirectResponse("/leaves?error=forbidden", status_code=302)

        allowed = await user_has_permission(db, current_user.id, "leaves.approve")
        if not (getattr(current_user, "is_admin", False) or allowed):
            return RedirectResponse("/leaves?error=forbidden", status_code=302)

        lr = (await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))).scalar_one_or_none()
        if not lr:
            return RedirectResponse("/leaves?error=not_found", status_code=302)

        lr.status = "rejected"
        lr.approved_by = current_user.id
        lr.decided_at = datetime.utcnow()
        await db.commit()

        return RedirectResponse(f"/leaves?employee_id={lr.employee_id}&success=1", status_code=302)
