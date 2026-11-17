from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class RolUsuario(str, Enum):
    admin = "admin"
    bibliotecario = "bibliotecario"
    socio = "socio"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(150), nullable=False)

    __table_args__ = (
        Index("ix_usuarios_email_lower", func.lower(email), unique=True),
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        SAEnum(RolUsuario, name="rolusuario"),
        nullable=False,
        default=RolUsuario.socio,
        server_default=RolUsuario.socio.value,
    )
    activo: Mapped[bool] = mapped_column(default=True, nullable=False, server_default="true")
    intentos_fallidos: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    socio_id: Mapped[int | None] = mapped_column(ForeignKey("socios.id"), unique=True, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    socio: Mapped["Socio | None"] = relationship(back_populates="usuario")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="usuario")
    prestamos_registrados: Mapped[list["Prestamo"]] = relationship(
        back_populates="registrado_por"
    )
