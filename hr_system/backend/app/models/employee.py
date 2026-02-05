from sqlalchemy import String, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    job_title: Mapped[str] = mapped_column(String(200), default="")
    hire_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # ✅ NEW
    base_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    department = relationship("Department")
