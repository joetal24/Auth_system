from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BackupCode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backup_code"

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    hashed_code: Mapped[str] = mapped_column(String(255), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="backup_codes")
