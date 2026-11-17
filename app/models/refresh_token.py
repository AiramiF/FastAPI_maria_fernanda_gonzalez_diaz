from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="refresh_tokens")
