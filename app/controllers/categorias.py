from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import Conflicto, NoEncontrado
from ..models.categoria import Categoria
from ..schemas.categoria import CategoriaCreate, CategoriaPatch, CategoriaRead
from ..schemas.pagina import Pagina


def listar_categorias(db: Session, skip: int, limit: int) -> Pagina[CategoriaRead]:
    statement = select(Categoria)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    items = db.scalars(statement.order_by(Categoria.id).offset(skip).limit(limit)).all()
    return Pagina(items=list(items), total=int(total or 0), skip=skip, limit=limit)


def obtener_categoria(db: Session, categoria_id: int) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise NoEncontrado("Categoría no encontrada")
    return categoria


def crear_categoria(db: Session, datos: CategoriaCreate) -> Categoria:
    if db.scalar(
        select(Categoria.id).where(Categoria.nombre == datos.nombre)
    ) is not None:
        raise Conflicto("La categoría ya existe")
    categoria = Categoria(**datos.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def actualizar_categoria(
    db: Session, categoria_id: int, datos: CategoriaPatch
) -> Categoria:
    categoria = obtener_categoria(db, categoria_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios and db.scalar(
        select(Categoria.id).where(
            Categoria.nombre == cambios["nombre"], Categoria.id != categoria_id
        )
    ) is not None:
        raise Conflicto("La categoría ya existe")
    for campo, valor in cambios.items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria


def eliminar_categoria(db: Session, categoria_id: int) -> None:
    categoria = obtener_categoria(db, categoria_id)
    categoria.libros.clear()
    db.delete(categoria)
    db.commit()
