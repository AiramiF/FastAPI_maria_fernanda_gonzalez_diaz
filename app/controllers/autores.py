from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import Conflicto, NoEncontrado
from ..models.autor import Autor
from ..schemas.autor import AutorCreate, AutorPatch, AutorRead
from ..schemas.pagina import Pagina


def listar_autores(
    db: Session, skip: int, limit: int, nacionalidad: str | None = None
) -> Pagina[AutorRead]:
    statement = select(Autor)
    if nacionalidad:
        statement = statement.where(Autor.nacionalidad.ilike(f"%{nacionalidad}%"))
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    items = db.scalars(statement.order_by(Autor.id).offset(skip).limit(limit)).all()
    return Pagina(items=list(items), total=int(total or 0), skip=skip, limit=limit)


def obtener_autor(db: Session, autor_id: int) -> Autor:
    autor = db.get(Autor, autor_id)
    if autor is None:
        raise NoEncontrado("Autor no encontrado")
    return autor


def crear_autor(db: Session, datos: AutorCreate) -> Autor:
    if db.scalar(select(Autor.id).where(Autor.nombre == datos.nombre)) is not None:
        raise Conflicto("El autor ya existe")
    autor = Autor(**datos.model_dump())
    db.add(autor)
    db.commit()
    db.refresh(autor)
    return autor


def actualizar_autor(db: Session, autor_id: int, datos: AutorPatch) -> Autor:
    autor = obtener_autor(db, autor_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios and db.scalar(
        select(Autor.id).where(
            Autor.nombre == cambios["nombre"], Autor.id != autor_id
        )
    ) is not None:
        raise Conflicto("El autor ya existe")
    for campo, valor in cambios.items():
        setattr(autor, campo, valor)
    db.commit()
    db.refresh(autor)
    return autor


def eliminar_autor(db: Session, autor_id: int) -> None:
    autor = obtener_autor(db, autor_id)
    if autor.libros:
        raise Conflicto("No se puede eliminar un autor con libros")
    db.delete(autor)
    db.commit()
