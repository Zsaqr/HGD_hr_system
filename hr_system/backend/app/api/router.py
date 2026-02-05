from fastapi import APIRouter

from app.api.endpoints import auth, employees, departments, leaves, payroll, reports, rbac_admin
from app.routers import attendance
from app.api.endpoints import auth, employees, departments, leaves, payroll, reports, rbac_admin, admin_users


router = APIRouter()
router.include_router(auth.router)

router.include_router(departments.router, prefix="/departments", tags=["departments"])
router.include_router(employees.router, prefix="/employees", tags=["employees"])
router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])

router.include_router(leaves.router, prefix="/leaves", tags=["leaves"])
router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])

router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(rbac_admin.router, prefix="/rbac", tags=["rbac"])

router.include_router(admin_users.router, prefix="/users", tags=["users"])
