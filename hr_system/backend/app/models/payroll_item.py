from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayrollItem(Base):
    __tablename__ = "payroll_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)

    base_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    allowances_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    deductions_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run = relationship("PayrollRun")
    employee = relationship("Employee")
