from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .categoria import libro_categoria


class Libro(Base):
    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    isbn: Mapped[str] = mapped_column(String(13), unique=True, nullable=False)
    anio_publicacion: Mapped[int] = mapped_column(Integer, nullable=False)
    ejemplares: Mapped[int] = mapped_column(Integer, nullable=False)
    autor_id: Mapped[int] = mapped_column(ForeignKey("autores.id"), nullable=False)
    portada_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    portada_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    autor: Mapped["Autor"] = relationship(back_populates="libros")
    categorias: Mapped[list["Categoria"]] = relationship(
        secondary=libro_categoria,
        back_populates="libros",
    )
    prestamos: Mapped[list["Prestamo"]] = relationship(
        back_populates="libro",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
