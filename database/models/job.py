from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.main import Base


class Jobs(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)

