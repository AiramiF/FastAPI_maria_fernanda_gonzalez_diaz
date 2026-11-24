from ..core.exceptions import Conflicto, NoEncontrado
from ..core.mongodb import Repository
from ..schemas.categoria import CategoriaCreate, CategoriaPatch
from ..schemas.pagina import Pagina


def listar_categorias(db: Repository, skip: int, limit: int) -> Pagina:
    items = list(db.collection("categorias").find({}, {"_id": 0}).sort("id", 1))
    return Pagina(items=items[skip : skip + limit], total=len(items), skip=skip, limit=limit)


def obtener_categoria(db: Repository, categoria_id: int) -> dict:
    category = db.get("categorias", categoria_id)
    if category is None:
        raise NoEncontrado("Categoría no encontrada")
    return category


def crear_categoria(db: Repository, datos: CategoriaCreate) -> dict:
    if db.collection("categorias").find_one({"nombre": datos.nombre}):
        raise Conflicto("La categoría ya existe")
    return db.insert("categorias", datos.model_dump())


def actualizar_categoria(db: Repository, categoria_id: int, datos: CategoriaPatch) -> dict:
    obtener_categoria(db, categoria_id)
    changes = datos.model_dump(exclude_unset=True)
    if "nombre" in changes and db.collection("categorias").find_one(
        {"nombre": changes["nombre"], "id": {"$ne": categoria_id}}
    ):
        raise Conflicto("La categoría ya existe")
    return db.update("categorias", categoria_id, changes) or obtener_categoria(
        db, categoria_id
    )


def eliminar_categoria(db: Repository, categoria_id: int) -> None:
    obtener_categoria(db, categoria_id)
    for book in db.collection("libros").find(
        {"categoria_ids": categoria_id}, {"_id": 0}
    ):
        db.update(
            "libros",
            book["id"],
            {
                "categoria_ids": [
                    item for item in book.get("categoria_ids", []) if item != categoria_id
                ]
            },
        )
    db.delete("categorias", categoria_id)
