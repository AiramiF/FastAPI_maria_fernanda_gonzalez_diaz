import logging
from typing import Any

from ..core import cloudinary
from ..core.exceptions import Conflicto, NoEncontrado, ReglaNegocio, ServicioExternoError
from ..core.mongodb import Repository
from ..schemas.libro import LibroCreate, LibroPatch, LibroRead
from ..schemas.pagina import Pagina

logger = logging.getLogger(__name__)


def _obtener(db: Repository, libro_id: int) -> dict[str, Any]:
    book = db.get("libros", libro_id)
    if book is None:
        raise NoEncontrado("Libro no encontrado")
    return book


def _respuesta(db: Repository, book: dict[str, Any]) -> LibroRead:
    author = db.get("autores", book["autor_id"])
    if author is None:
        raise NoEncontrado("Autor no encontrado")
    categories = [
        db.get("categorias", category_id)
        for category_id in book.get("categoria_ids", [])
    ]
    active_loans = db.collection("prestamos").count_documents(
        {"libro_id": book["id"], "fecha_devolucion": None}
    )
    return LibroRead(
        id=book["id"],
        titulo=book["titulo"],
        isbn=book["isbn"],
        anio_publicacion=book["anio_publicacion"],
        ejemplares=book["ejemplares"],
        disponibles=book["ejemplares"] - active_loans,
        portada_url=book.get("portada_url"),
        autor=author,
        categorias=[category for category in categories if category is not None],
    )


def listar_libros(
    db: Repository,
    skip: int,
    limit: int,
    buscar: str | None = None,
    autor: str | None = None,
    categoria_id: int | None = None,
    desde: int | None = None,
    hasta: int | None = None,
    orden: str = "titulo",
) -> Pagina:
    items = list(db.collection("libros").find({}, {"_id": 0}))
    if buscar:
        needle = buscar.casefold()
        items = [book for book in items if needle in book["titulo"].casefold()]
    if autor:
        needle = autor.casefold()
        items = [
            book
            for book in items
            if (db.get("autores", book["autor_id"]) or {}).get("nombre", "")
            .casefold()
            .find(needle)
            >= 0
        ]
    if categoria_id is not None:
        items = [book for book in items if categoria_id in book.get("categoria_ids", [])]
    if desde is not None:
        items = [book for book in items if book["anio_publicacion"] >= desde]
    if hasta is not None:
        items = [book for book in items if book["anio_publicacion"] <= hasta]
    if orden == "anio":
        items.sort(key=lambda book: (book["anio_publicacion"], book["id"]))
    elif orden == "-anio":
        items.sort(key=lambda book: (-book["anio_publicacion"], book["id"]))
    else:
        items.sort(key=lambda book: (book["titulo"].casefold(), book["id"]))
    total = len(items)
    return Pagina(
        items=[_respuesta(db, book) for book in items[skip : skip + limit]],
        total=total,
        skip=skip,
        limit=limit,
    )


def obtener_libro(db: Repository, libro_id: int) -> LibroRead:
    return _respuesta(db, _obtener(db, libro_id))


def listar_libros_autor(
    db: Repository, autor_id: int, skip: int, limit: int
) -> Pagina:
    if db.get("autores", autor_id) is None:
        raise NoEncontrado("Autor no encontrado")
    items = list(
        db.collection("libros")
        .find({"autor_id": autor_id}, {"_id": 0})
        .sort("id", 1)
    )
    return Pagina(
        items=[_respuesta(db, book) for book in items[skip : skip + limit]],
        total=len(items),
        skip=skip,
        limit=limit,
    )


def crear_libro(db: Repository, datos: LibroCreate) -> LibroRead:
    if db.get("autores", datos.autor_id) is None:
        raise NoEncontrado("Autor no encontrado")
    if any(db.get("categorias", category_id) is None for category_id in datos.categoria_ids):
        raise NoEncontrado("Categoría no encontrada")
    if db.collection("libros").find_one({"isbn": datos.isbn}):
        raise Conflicto("El ISBN ya existe")
    fields = datos.model_dump(exclude={"categoria_ids"})
    book = db.insert(
        "libros",
        {
            **fields,
            "categoria_ids": datos.categoria_ids,
            "portada_url": None,
            "portada_public_id": None,
        },
    )
    return _respuesta(db, book)


def actualizar_libro(db: Repository, libro_id: int, datos: LibroPatch) -> LibroRead:
    book = _obtener(db, libro_id)
    changes = datos.model_dump(exclude_unset=True)
    if "autor_id" in changes and db.get("autores", changes["autor_id"]) is None:
        raise NoEncontrado("Autor no encontrado")
    if "isbn" in changes and db.collection("libros").find_one(
        {"isbn": changes["isbn"], "id": {"$ne": libro_id}}
    ):
        raise Conflicto("El ISBN ya existe")
    if "categoria_ids" in changes and any(
        db.get("categorias", category_id) is None
        for category_id in changes["categoria_ids"]
    ):
        raise NoEncontrado("Categoría no encontrada")
    active_loans = db.collection("prestamos").count_documents(
        {"libro_id": libro_id, "fecha_devolucion": None}
    )
    if changes.get("ejemplares", book["ejemplares"]) < active_loans:
        raise ReglaNegocio(
            "Los ejemplares no pueden ser menores que los préstamos activos"
        )
    updated = db.update("libros", libro_id, changes)
    return _respuesta(db, updated or _obtener(db, libro_id))


def eliminar_libro(db: Repository, libro_id: int) -> None:
    _obtener(db, libro_id)
    if db.collection("prestamos").count_documents(
        {"libro_id": libro_id, "fecha_devolucion": None}
    ):
        raise Conflicto("No se puede eliminar un libro con préstamos sin devolver")
    loans = list(
        db.collection("prestamos").find({"libro_id": libro_id}, {"_id": 0})
    )
    loan_ids = [loan["id"] for loan in loans]
    if loan_ids:
        db.collection("multas").delete_many({"prestamo_id": {"$in": loan_ids}})
        db.collection("prestamos").delete_many({"id": {"$in": loan_ids}})
    db.delete("libros", libro_id)


def subir_portada(db: Repository, libro_id: int, contenido: bytes) -> LibroRead:
    book = _obtener(db, libro_id)
    url, public_id = cloudinary.subir_portada(contenido)
    try:
        updated = db.update(
            "libros",
            libro_id,
            {"portada_url": url, "portada_public_id": public_id},
        )
        if updated is None:
            raise NoEncontrado("Libro no encontrado")
    except Exception:
        try:
            cloudinary.eliminar_portada(public_id)
        except ServicioExternoError:
            logger.exception("No se pudo limpiar una portada tras fallar su guardado")
        raise
    old_public_id = book.get("portada_public_id")
    if old_public_id:
        cloudinary.eliminar_portada(old_public_id)
    return _respuesta(db, updated)


def eliminar_portada(db: Repository, libro_id: int) -> None:
    book = _obtener(db, libro_id)
    public_id = book.get("portada_public_id")
    if public_id:
        cloudinary.eliminar_portada(public_id)
    db.update(
        "libros",
        libro_id,
        {"portada_url": None, "portada_public_id": None},
    )
