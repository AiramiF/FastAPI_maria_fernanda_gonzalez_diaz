from ..core.exceptions import Conflicto, NoEncontrado
from ..core.mongodb import Repository
from ..schemas.autor import AutorCreate, AutorPatch
from ..schemas.pagina import Pagina


def listar_autores(
    db: Repository, skip: int, limit: int, nacionalidad: str | None = None
) -> Pagina:
    items = list(db.collection("autores").find({}, {"_id": 0}))
    if nacionalidad:
        needle = nacionalidad.casefold()
        items = [item for item in items if needle in (item.get("nacionalidad") or "").casefold()]
    items.sort(key=lambda item: item["id"])
    return Pagina(items=items[skip : skip + limit], total=len(items), skip=skip, limit=limit)


def obtener_autor(db: Repository, autor_id: int) -> dict:
    autor = db.get("autores", autor_id)
    if autor is None:
        raise NoEncontrado("Autor no encontrado")
    return autor


def crear_autor(db: Repository, datos: AutorCreate) -> dict:
    if db.collection("autores").find_one({"nombre": datos.nombre}):
        raise Conflicto("El autor ya existe")
    return db.insert("autores", datos.model_dump())


def actualizar_autor(db: Repository, autor_id: int, datos: AutorPatch) -> dict:
    obtener_autor(db, autor_id)
    changes = datos.model_dump(exclude_unset=True)
    if "nombre" in changes and db.collection("autores").find_one(
        {"nombre": changes["nombre"], "id": {"$ne": autor_id}}
    ):
        raise Conflicto("El autor ya existe")
    return db.update("autores", autor_id, changes) or obtener_autor(db, autor_id)


def eliminar_autor(db: Repository, autor_id: int) -> None:
    obtener_autor(db, autor_id)
    if db.collection("libros").find_one({"autor_id": autor_id}):
        raise Conflicto("No se puede eliminar un autor con libros")
    db.delete("autores", autor_id)
