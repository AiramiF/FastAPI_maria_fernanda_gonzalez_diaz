from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id", ondelete="CASCADE"), nullable=False
    )
    socio_id: Mapped[int] = mapped_column(
        ForeignKey("socios.id"), nullable=False
    )
    fecha_prestamo: Mapped[date] = mapped_column(
        Date, default=date.today, nullable=False
    )
    fecha_limite: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_devolucion: Mapped[date | None] = mapped_column(Date)
    multa: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    multa_pagada: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    registrado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    libro: Mapped["Libro"] = relationship(back_populates="prestamos")
    socio: Mapped["Socio"] = relationship(back_populates="prestamos")
    registrado_por: Mapped["Usuario | None"] = relationship(
        back_populates="prestamos_registrados"
    )
