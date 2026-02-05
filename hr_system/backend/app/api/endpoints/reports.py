from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.endpoints.auth import require_login
from app.models.audit_log import AuditLog

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/audit")
async def audit_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    async for db in get_db():
        db: AsyncSession
        items = (await db.execute(
            select(AuditLog).order_by(desc(AuditLog.created_at)).limit(50)
        )).scalars().all()

        return templates.TemplateResponse(
            "audit.html",
            {"request": request, "items": items},
        )
