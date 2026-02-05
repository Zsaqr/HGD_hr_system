from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)

    leave_type: Mapped[str] = mapped_column(String(50), default="annual", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee")
    approver = relationship("User", foreign_keys=[approved_by])
